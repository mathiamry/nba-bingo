/**
 * NBA Bingo — serveur PartyKit (Cloudflare Workers + Durable Objects).
 *
 * MODE RACE ASYNC :
 * - Tout le monde joue la MÊME grille avec la MÊME séquence de joueurs.
 * - Chacun progresse à SON rythme (turn index par joueur, timer par joueur).
 * - La partie se termine globalement quand TOUS les joueurs ont fini
 *   (grille pleine OU séquence épuisée).
 * - Les erreurs restent vertes pendant le jeu, révélées en rouge à la fin.
 * - Score = nb cases correctes × pointsPerCell (3.75 → max 60).
 */

import type * as Party from "partykit/server";
import gamesPool from "./games.json";

// ─── Types ───────────────────────────────────────────────────────────────

type Cell = {
  id: string;
  label: string;
  axis: string;
  difficulty: number;
  points: number;
};

type SequenceEntry = {
  id: number;
  name: string;
  validCellIds: string[];
};

type Game = {
  cells: Cell[];
  sequence: SequenceEntry[];
};

type Rules = {
  maxStrikes: number;
  gridSize: number;
  totalPerfectScore: number;
  pointsPerCell: number;
  secondsPerTurn: number;
};

type GamesPool = {
  rules: Rules;
  games: Game[];
};

const POOL = gamesPool as GamesPool;

type Status = "lobby" | "playing" | "ended";

type Player = {
  id: string;
  name: string;
  joinedAt: number;
};

type Placement = {
  cellId: string | null;
  wasCorrect: boolean | null;
  turnIndex: number;
};

type RoomState = {
  status: Status;
  hostId: string | null;
  players: Record<string, Player>;
  game: Game | null;
  startedAt: number; // ms epoch — pour calculer le temps de completion
  // Progression INDIVIDUELLE par joueur (race async)
  playerTurnIndex: Record<string, number>;
  playerTurnEndsAt: Record<string, number>;
  playerDone: Record<string, boolean>;
  playerCompletedAt: Record<string, number>; // ms epoch — tiebreaker
  placements: Record<string, Placement[]>;
};

// ─── Vue par destinataire ────────────────────────────────────────────────

type CellView = {
  status: "empty" | "filled" | "wrong";
  playerName: string | null;
  turnIndex: number | null;
};

type LeaderboardEntry = {
  id: string;
  name: string;
  placed: number;
  skipped: number;        // cases laissées vides (skip + timeout)
  done: boolean;
  correct: number;        // 0 tant que reveal=false
  score: number;          // idem
  completedAtMs: number;  // 0 si pas encore done
  durationMs: number;     // temps écoulé entre start et done (0 si pas done)
};

function viewForRecipient(state: RoomState, recipientId: string) {
  const reveal = state.status === "ended";
  const myTurn = state.playerTurnIndex[recipientId] ?? 0;
  const myEndsAt = state.playerTurnEndsAt[recipientId] ?? 0;
  const myDone = state.playerDone[recipientId] === true;
  const myPlacements = state.placements[recipientId] || [];

  // Grille du destinataire (uniquement SES placements visibles)
  const cellStates: Record<string, CellView> = {};
  if (state.game) {
    for (const c of state.game.cells) {
      cellStates[c.id] = { status: "empty", playerName: null, turnIndex: null };
    }
    for (const p of myPlacements) {
      if (p.cellId === null) continue;
      const visualStatus =
        reveal && p.wasCorrect === false ? "wrong" : "filled";
      cellStates[p.cellId] = {
        status: visualStatus,
        playerName: state.game.sequence[p.turnIndex]?.name ?? null,
        turnIndex: p.turnIndex,
      };
    }
  }

  // Joueur actuel = sequence[mon turnIndex] (chacun voit le sien)
  const currentPlayer =
    state.game && state.status === "playing" && !myDone
      ? state.game.sequence[myTurn] ?? null
      : null;

  // Map cellId → points pour le calcul de score (variable par case selon
  // la difficulté, somme exacte = 60).
  const pointsByCell = new Map<string, number>();
  if (state.game) {
    for (const c of state.game.cells) pointsByCell.set(c.id, c.points);
  }

  // Leaderboard : progression de tous (placed = posées, done flag, score au reveal)
  const leaderboard: LeaderboardEntry[] = Object.values(state.players).map(
    (p) => {
      const places = state.placements[p.id] || [];
      const placed = places.filter((pl) => pl.cellId !== null).length;
      const skipped = places.filter((pl) => pl.cellId === null).length;
      const correctPlaces = places.filter((pl) => pl.wasCorrect === true);
      const correct = correctPlaces.length;
      const score = correctPlaces.reduce(
        (s, pl) => s + (pointsByCell.get(pl.cellId!) ?? 0),
        0,
      );
      const completedAtMs = state.playerCompletedAt[p.id] ?? 0;
      const durationMs =
        completedAtMs && state.startedAt
          ? completedAtMs - state.startedAt
          : 0;
      return {
        id: p.id,
        name: p.name,
        placed,
        skipped,
        done: state.playerDone[p.id] === true,
        correct: reveal ? correct : 0,
        score: reveal ? score : 0,
        completedAtMs: reveal ? completedAtMs : 0,
        durationMs: reveal ? durationMs : 0,
      };
    },
  );

  const totalPlayers = Object.keys(state.players).length;
  const doneCount = Object.values(state.playerDone).filter(Boolean).length;

  return {
    status: state.status,
    hostId: state.hostId,
    selfId: recipientId,
    isHost: state.hostId === recipientId,
    isDone: myDone,
    doneCount,
    totalPlayers,
    players: Object.values(state.players).sort(
      (a, b) => a.joinedAt - b.joinedAt,
    ),
    cells: state.game?.cells ?? [],
    cellStates,
    sequenceLength: state.game?.sequence.length ?? 0,
    currentPlayer,
    turnIndex: myTurn,
    turnEndsAt: myEndsAt,
    serverTime: Date.now(),
    leaderboard,
    rules: POOL.rules,
  };
}

// ─── Server ──────────────────────────────────────────────────────────────

export default class NbaBingoServer implements Party.Server {
  state: RoomState;
  playerTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();
  // Mapping conn.id ↔ sessionId pour permettre la reconnexion :
  // l'identité d'un joueur est portée par un sessionId stable côté client
  // (généré dans localStorage), pas par conn.id qui change à chaque WS.
  sessionByConn: Map<string, string> = new Map();
  connsBySession: Map<string, Set<string>> = new Map();

  constructor(readonly room: Party.Room) {
    this.state = {
      status: "lobby",
      hostId: null,
      players: {},
      game: null,
      startedAt: 0,
      playerTurnIndex: {},
      playerTurnEndsAt: {},
      playerDone: {},
      playerCompletedAt: {},
      placements: {},
    };
  }

  // Récupère le sessionId associé à une connexion. Si le client n'a pas
  // encore envoyé son join, retourne "" (spectateur anonyme).
  private sessionOf(conn: Party.Connection): string {
    return this.sessionByConn.get(conn.id) ?? "";
  }

  onConnect(conn: Party.Connection) {
    // Pas de sessionId encore, mais on envoie le state pour que le
    // client voie au moins l'état du lobby/score s'il y en a un.
    this.sendStateTo(conn);
  }

  onClose(conn: Party.Connection) {
    const sessionId = this.sessionByConn.get(conn.id);
    this.sessionByConn.delete(conn.id);
    if (!sessionId) return;
    const conns = this.connsBySession.get(sessionId);
    if (conns) {
      conns.delete(conn.id);
      if (conns.size === 0) this.connsBySession.delete(sessionId);
    }
    // Toujours connecté ailleurs (autre onglet) ? On ne touche rien.
    if (this.connsBySession.has(sessionId)) {
      this.broadcast();
      return;
    }
    // Plus aucune connexion pour ce joueur :
    // - en LOBBY on supprime (sinon liste polluée par des fantômes)
    // - en PLAYING/ENDED on garde l'état pour permettre la reconnexion
    if (this.state.status === "lobby") {
      this.removePlayer(sessionId);
    } else {
      this.broadcast();
    }
  }

  onMessage(raw: string, sender: Party.Connection) {
    let msg: any;
    try {
      msg = JSON.parse(raw);
    } catch {
      return;
    }
    switch (msg?.type) {
      case "join":
        this.handleJoin(
          sender,
          sanitizeName(msg.name),
          sanitizeSessionId(msg.sessionId),
        );
        break;
      case "start":
        this.handleStart(sender);
        break;
      case "place":
        this.handlePlace(sender, String(msg.cellId || ""));
        break;
      case "skip":
        this.handleSkip(sender);
        break;
      case "restart":
        this.handleRestart(sender);
        break;
    }
  }

  // ─── Lobby ─────────────────────────────────────────────────────────────

  handleJoin(conn: Party.Connection, name: string, sessionId: string) {
    if (!name || !sessionId) return;

    // Associe la connexion au sessionId du joueur.
    this.sessionByConn.set(conn.id, sessionId);
    if (!this.connsBySession.has(sessionId)) {
      this.connsBySession.set(sessionId, new Set());
    }
    this.connsBySession.get(sessionId)!.add(conn.id);

    const isExistingPlayer = !!this.state.players[sessionId];

    if (isExistingPlayer) {
      // Reconnexion : on garde tout (placements, score, turn), juste le
      // nom est éventuellement mis à jour.
      this.state.players[sessionId].name = name;
      this.broadcast();
      return;
    }

    // Nouveau visiteur :
    // - en lobby : on l'inscrit comme joueur
    // - en playing : on l'inscrit aussi mais il démarre tout de suite
    //   au tour 0 (race async, il peut rattraper)
    // - en ended : il reste SPECTATEUR (pas de player record), il voit
    //   le leaderboard final mais ne pollue pas le classement
    if (this.state.status === "ended") {
      this.broadcast();
      return;
    }

    this.state.players[sessionId] = {
      id: sessionId,
      name,
      joinedAt: Date.now(),
    };
    this.state.placements[sessionId] = [];
    this.state.playerTurnIndex[sessionId] = 0;
    this.state.playerTurnEndsAt[sessionId] = 0;
    this.state.playerDone[sessionId] = false;
    this.state.playerCompletedAt[sessionId] = 0;
    if (!this.state.hostId) this.state.hostId = sessionId;

    if (this.state.status === "playing" && this.state.game) {
      this.beginPlayerTurn(sessionId);
    }
    this.broadcast();
  }

  removePlayer(sessionId: string) {
    if (!this.state.players[sessionId]) return;
    this.clearPlayerTimer(sessionId);
    delete this.state.players[sessionId];
    delete this.state.placements[sessionId];
    delete this.state.playerTurnIndex[sessionId];
    delete this.state.playerTurnEndsAt[sessionId];
    delete this.state.playerDone[sessionId];
    delete this.state.playerCompletedAt[sessionId];
    if (this.state.hostId === sessionId) {
      const remaining = Object.keys(this.state.players);
      this.state.hostId = remaining[0] ?? null;
    }
    if (Object.keys(this.state.players).length === 0) {
      this.resetToLobby();
    } else if (this.state.status === "playing" && this.allPlayersDone()) {
      this.endGame();
      return;
    }
    this.broadcast();
  }

  // ─── Start / restart ───────────────────────────────────────────────────

  handleStart(sender: Party.Connection) {
    if (this.sessionOf(sender) !== this.state.hostId) return;
    if (this.state.status !== "lobby") return;
    if (Object.keys(this.state.players).length === 0) return;
    if (POOL.games.length === 0) return;

    this.state.game = POOL.games[Math.floor(Math.random() * POOL.games.length)];
    this.state.status = "playing";
    this.state.startedAt = Date.now();

    for (const id of Object.keys(this.state.players)) {
      this.state.placements[id] = [];
      this.state.playerTurnIndex[id] = 0;
      this.state.playerTurnEndsAt[id] = 0;
      this.state.playerDone[id] = false;
      this.state.playerCompletedAt[id] = 0;
      this.beginPlayerTurn(id);
    }
    this.broadcast();
  }

  handleRestart(sender: Party.Connection) {
    if (this.sessionOf(sender) !== this.state.hostId) return;
    if (this.state.status !== "ended") return;
    this.resetToLobby();
    this.broadcast();
  }

  resetToLobby() {
    for (const id of this.playerTimers.keys()) this.clearPlayerTimer(id);
    this.state.status = "lobby";
    this.state.game = null;
    this.state.startedAt = 0;
    for (const id of Object.keys(this.state.players)) {
      this.state.placements[id] = [];
      this.state.playerTurnIndex[id] = 0;
      this.state.playerTurnEndsAt[id] = 0;
      this.state.playerDone[id] = false;
      this.state.playerCompletedAt[id] = 0;
    }
  }

  // ─── Per-player turn loop ──────────────────────────────────────────────

  beginPlayerTurn(playerId: string) {
    if (!this.state.game) return;
    if (this.state.status !== "playing") return;
    if (this.state.playerDone[playerId]) return;

    const turn = this.state.playerTurnIndex[playerId] ?? 0;
    if (turn >= this.state.game.sequence.length) {
      this.markPlayerDone(playerId);
      return;
    }
    const placed = (this.state.placements[playerId] || []).filter(
      (p) => p.cellId !== null,
    ).length;
    if (placed >= POOL.rules.gridSize) {
      this.markPlayerDone(playerId);
      return;
    }

    this.state.playerTurnEndsAt[playerId] =
      Date.now() + POOL.rules.secondsPerTurn * 1000;
    this.clearPlayerTimer(playerId);
    this.playerTimers.set(
      playerId,
      setTimeout(
        () => this.advancePlayerTurn(playerId),
        POOL.rules.secondsPerTurn * 1000,
      ),
    );
  }

  advancePlayerTurn(playerId: string) {
    if (!this.state.players[playerId]) return;
    if (this.state.playerDone[playerId]) return;
    this.clearPlayerTimer(playerId);
    this.state.playerTurnIndex[playerId] =
      (this.state.playerTurnIndex[playerId] ?? 0) + 1;
    this.beginPlayerTurn(playerId);
    this.broadcast();
  }

  markPlayerDone(playerId: string) {
    if (!this.state.players[playerId]) return;
    if (this.state.playerDone[playerId]) return;
    this.clearPlayerTimer(playerId);
    this.state.playerDone[playerId] = true;
    this.state.playerTurnEndsAt[playerId] = 0;
    this.state.playerCompletedAt[playerId] = Date.now();
    if (this.allPlayersDone()) {
      this.endGame();
    }
  }

  allPlayersDone(): boolean {
    const ids = Object.keys(this.state.players);
    if (ids.length === 0) return false;
    return ids.every((id) => this.state.playerDone[id] === true);
  }

  endGame() {
    for (const id of this.playerTimers.keys()) this.clearPlayerTimer(id);
    this.state.status = "ended";
    this.broadcast();
  }

  clearPlayerTimer(playerId: string) {
    const t = this.playerTimers.get(playerId);
    if (t) {
      clearTimeout(t);
      this.playerTimers.delete(playerId);
    }
  }

  // ─── Placements ────────────────────────────────────────────────────────

  handlePlace(sender: Party.Connection, cellId: string) {
    if (this.state.status !== "playing" || !this.state.game) return;
    const playerId = this.sessionOf(sender);
    if (!playerId || !this.state.players[playerId]) return;
    if (this.state.playerDone[playerId]) return;

    const myTurn = this.state.playerTurnIndex[playerId] ?? 0;
    const seq = this.state.game.sequence[myTurn];
    if (!seq) return;

    const placements = this.state.placements[playerId] || [];
    if (placements.some((p) => p.cellId === cellId)) return;

    const wasCorrect = seq.validCellIds.includes(cellId);
    placements.push({ cellId, wasCorrect, turnIndex: myTurn });
    this.state.placements[playerId] = placements;

    this.advancePlayerTurn(playerId);
  }

  handleSkip(sender: Party.Connection) {
    if (this.state.status !== "playing" || !this.state.game) return;
    const playerId = this.sessionOf(sender);
    if (!playerId || !this.state.players[playerId]) return;
    if (this.state.playerDone[playerId]) return;

    const myTurn = this.state.playerTurnIndex[playerId] ?? 0;
    const placements = this.state.placements[playerId] || [];
    placements.push({ cellId: null, wasCorrect: null, turnIndex: myTurn });
    this.state.placements[playerId] = placements;

    this.advancePlayerTurn(playerId);
  }

  // ─── Wire ──────────────────────────────────────────────────────────────

  sendStateTo(conn: Party.Connection) {
    const sessionId = this.sessionOf(conn);
    const view = viewForRecipient(this.state, sessionId);
    conn.send(JSON.stringify({ type: "state", state: view }));
  }

  broadcast() {
    for (const conn of this.room.getConnections()) {
      this.sendStateTo(conn);
    }
  }
}

NbaBingoServer satisfies Party.Worker;

// ─── Helpers ─────────────────────────────────────────────────────────────

function sanitizeName(raw: unknown): string {
  if (typeof raw !== "string") return "";
  return raw.trim().slice(0, 24);
}

function sanitizeSessionId(raw: unknown): string {
  if (typeof raw !== "string") return "";
  // Doit ressembler à un UUID/token : alphanum + tirets + underscore.
  const cleaned = raw.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 64);
  return cleaned;
}
