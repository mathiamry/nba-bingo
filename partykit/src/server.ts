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

// Combien de temps on garde le record d'un joueur après sa dernière
// déconnexion. Un joueur qui change d'app, lock l'écran ou se reconnecte
// dans cette fenêtre retrouve TOUT (host status, placements, score).
// Au-delà, on considère qu'il a abandonné et on le retire (ce qui peut
// libérer le slot host pour d'autres). 10 min couvre largement le cas
// "je passe sur Slack 5 min" ou "le navigateur a tué la WS en background".
const STALE_PLAYER_TTL_MS = 10 * 60 * 1000;

type Status = "lobby" | "countdown" | "playing" | "ended";

// Durée du countdown avant que la partie démarre. Server-driven pour que
// tous les joueurs voient le même chiffre au même instant (à la latence
// réseau près, ~50ms). Côté client, le ticker à 100ms du store calcule
// le secondsLeft à partir de `countdownEndsAt - serverTime`.
const COUNTDOWN_MS = 10_000;

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
  // Instant absolu (ms epoch) où le countdown tombe à 0 et où la partie
  // démarre. 0 = pas de countdown en cours. Server-driven pour que tous
  // les clients voient exactement le même chiffre au même instant.
  countdownEndsAt: number;
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
  score: number;          // idem (score réel = cases correctes uniquement)
  // Score "provisoire" = somme des points des cases POSÉES (peu importe
  // correct/faux). Visible en live pour tout le monde pendant la partie ;
  // préserve le suspense (les cases fausses restent vertes jusqu'au reveal)
  // tout en donnant un feedback de progression chiffré.
  provisionalScore: number;
  completedAtMs: number;  // 0 si pas encore done
  durationMs: number;     // temps écoulé entre start et done (0 si pas done)
  connected: boolean;     // false = en cours de reconnexion (ou parti)
};

// Le record stocké dans `state.players` n'a pas de flag `connected` —
// il est calculé à la volée pour chaque destinataire dans la vue.
type PlayerView = Player & { connected: boolean };

function viewForRecipient(
  state: RoomState,
  recipientId: string,
  connectedSessions: Set<string>,
) {
  const reveal = state.status === "ended";
  const myTurn = state.playerTurnIndex[recipientId] ?? 0;
  const myEndsAt = state.playerTurnEndsAt[recipientId] ?? 0;
  const myDone = state.playerDone[recipientId] === true;
  const myPlacements = state.placements[recipientId] || [];

  // Grille du destinataire (uniquement SES placements visibles).
  // Reveal des erreurs dès que le destinataire a fini OU partie globale
  // terminée — chacun voit son verdict perso à l'instant où il finit, sans
  // attendre les autres.
  const myReveal = reveal || myDone;
  const cellStates: Record<string, CellView> = {};
  if (state.game) {
    for (const c of state.game.cells) {
      cellStates[c.id] = { status: "empty", playerName: null, turnIndex: null };
    }
    for (const p of myPlacements) {
      if (p.cellId === null) continue;
      const visualStatus =
        myReveal && p.wasCorrect === false ? "wrong" : "filled";
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

  // Leaderboard : progression de tous.
  // Politique de reveal :
  //   - Joueur ENCORE EN COURS : on n'expose que `placed`, `skipped`,
  //     `provisionalScore` (somme des points des cases posées, peu importe
  //     correct/faux). Préserve le suspense.
  //   - Joueur TERMINÉ (grille pleine ou séquence finie OU partie globale
  //     terminée) : on expose `correct`, `score` (réel), `completedAtMs`,
  //     `durationMs`. Tout le monde voit son score final se figer.
  const leaderboard: LeaderboardEntry[] = Object.values(state.players).map(
    (p) => {
      const places = state.placements[p.id] || [];
      const placedCells = places.filter((pl) => pl.cellId !== null);
      const placed = placedCells.length;
      const skipped = places.length - placed;
      const correctPlaces = places.filter((pl) => pl.wasCorrect === true);
      const correct = correctPlaces.length;
      const score = correctPlaces.reduce(
        (s, pl) => s + (pointsByCell.get(pl.cellId!) ?? 0),
        0,
      );
      const provisionalScore = placedCells.reduce(
        (s, pl) => s + (pointsByCell.get(pl.cellId!) ?? 0),
        0,
      );
      const entryDone = state.playerDone[p.id] === true;
      const entryReveal = reveal || entryDone;
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
        done: entryDone,
        correct: entryReveal ? correct : 0,
        score: entryReveal ? score : 0,
        provisionalScore,
        completedAtMs: entryReveal ? completedAtMs : 0,
        durationMs: entryReveal ? durationMs : 0,
        connected: connectedSessions.has(p.id),
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
    players: Object.values(state.players)
      .map(
        (p): PlayerView => ({ ...p, connected: connectedSessions.has(p.id) }),
      )
      .sort((a, b) => a.joinedAt - b.joinedAt),
    cells: state.game?.cells ?? [],
    cellStates,
    sequenceLength: state.game?.sequence.length ?? 0,
    currentPlayer,
    turnIndex: myTurn,
    turnEndsAt: myEndsAt,
    // 0 hors phase countdown ; sinon ms epoch absolu. Le client convertit
    // en secondsLeft via Math.ceil((countdownEndsAt - serverTime) / 1000).
    countdownEndsAt: state.status === "countdown" ? state.countdownEndsAt : 0,
    serverTime: Date.now(),
    leaderboard,
    rules: POOL.rules,
  };
}

// ─── Server ──────────────────────────────────────────────────────────────

export default class NbaBingoServer implements Party.Server {
  state: RoomState;
  playerTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();
  // Timer du countdown global. Un seul à la fois ; armé par handleStart,
  // désarmé si on retombe en lobby (ex : tous les joueurs partent).
  countdownTimer: ReturnType<typeof setTimeout> | null = null;
  // Mapping conn.id ↔ sessionId pour permettre la reconnexion :
  // l'identité d'un joueur est portée par un sessionId stable côté client
  // (généré dans localStorage), pas par conn.id qui change à chaque WS.
  sessionByConn: Map<string, string> = new Map();
  connsBySession: Map<string, Set<string>> = new Map();
  // Timers de cleanup TTL : armés quand la dernière connexion d'un joueur
  // se ferme, désarmés à la reconnexion. Si jamais ils explosent, on
  // retire vraiment le joueur (libère le slot host le cas échéant).
  staleCleanupTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

  constructor(readonly room: Party.Room) {
    this.state = {
      status: "lobby",
      hostId: null,
      players: {},
      game: null,
      startedAt: 0,
      countdownEndsAt: 0,
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
    // Plus aucune connexion pour ce joueur. On garde son record (host
    // status, placements, score…) intact PARTOUT (lobby, playing, ended)
    // pour permettre une reconnexion propre — utile sur mobile où la
    // WebSocket meurt dès qu'on switch d'app. Un timer TTL retire le
    // joueur seulement s'il ne revient jamais.
    if (this.state.players[sessionId]) {
      this.scheduleStaleCleanup(sessionId);
    }
    this.broadcast();
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

    // Le joueur revient avant l'expiration du TTL : on annule la suppression.
    this.clearStaleCleanup(sessionId);

    const isExistingPlayer = !!this.state.players[sessionId];

    if (isExistingPlayer) {
      // Reconnexion : on garde tout (host status, placements, score,
      // turn), seul le nom peut être mis à jour.
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
    this.clearStaleCleanup(sessionId);
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

  // ─── TTL cleanup (joueurs déconnectés) ─────────────────────────────────

  scheduleStaleCleanup(sessionId: string) {
    this.clearStaleCleanup(sessionId);
    this.staleCleanupTimers.set(
      sessionId,
      setTimeout(() => {
        this.staleCleanupTimers.delete(sessionId);
        // Le joueur n'est jamais revenu — on libère le slot. removePlayer
        // gère la réassignation host et le passage en endGame si tous les
        // restants ont fini.
        this.removePlayer(sessionId);
      }, STALE_PLAYER_TTL_MS),
    );
  }

  clearStaleCleanup(sessionId: string) {
    const t = this.staleCleanupTimers.get(sessionId);
    if (t) {
      clearTimeout(t);
      this.staleCleanupTimers.delete(sessionId);
    }
  }

  // ─── Start / restart ───────────────────────────────────────────────────

  handleStart(sender: Party.Connection) {
    if (this.sessionOf(sender) !== this.state.hostId) return;
    if (this.state.status !== "lobby") return;
    if (Object.keys(this.state.players).length === 0) return;
    if (POOL.games.length === 0) return;

    // On choisit la grille tout de suite (pas après le countdown) :
    // évite tout race "le host clique deux fois" et fige la partie.
    this.state.game = POOL.games[Math.floor(Math.random() * POOL.games.length)];
    this.state.status = "countdown";
    this.state.countdownEndsAt = Date.now() + COUNTDOWN_MS;

    // Reset des progressions perso dès maintenant : si quelqu'un rejoint
    // pendant le countdown il part avec un état propre.
    for (const id of Object.keys(this.state.players)) {
      this.state.placements[id] = [];
      this.state.playerTurnIndex[id] = 0;
      this.state.playerTurnEndsAt[id] = 0;
      this.state.playerDone[id] = false;
      this.state.playerCompletedAt[id] = 0;
    }

    this.clearCountdownTimer();
    this.countdownTimer = setTimeout(() => this.beginGame(), COUNTDOWN_MS);
    this.broadcast();
  }

  beginGame() {
    this.clearCountdownTimer();
    // Garde-fou : si on a quitté la phase countdown entre temps (reset
    // lobby parce que tous les joueurs sont partis), on ne fait rien.
    if (this.state.status !== "countdown") return;
    if (!this.state.game) return;

    this.state.status = "playing";
    this.state.startedAt = Date.now();
    this.state.countdownEndsAt = 0;

    for (const id of Object.keys(this.state.players)) {
      this.beginPlayerTurn(id);
    }
    this.broadcast();
  }

  clearCountdownTimer() {
    if (this.countdownTimer) {
      clearTimeout(this.countdownTimer);
      this.countdownTimer = null;
    }
  }

  handleRestart(sender: Party.Connection) {
    if (this.sessionOf(sender) !== this.state.hostId) return;
    if (this.state.status !== "ended") return;
    this.resetToLobby();
    this.broadcast();
  }

  resetToLobby() {
    for (const id of this.playerTimers.keys()) this.clearPlayerTimer(id);
    this.clearCountdownTimer();
    this.state.status = "lobby";
    this.state.game = null;
    this.state.startedAt = 0;
    this.state.countdownEndsAt = 0;
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
    const connectedSessions = new Set(this.connsBySession.keys());
    const view = viewForRecipient(this.state, sessionId, connectedSessions);
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
