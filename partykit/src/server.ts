/**
 * NBA Bingo — serveur PartyKit (Cloudflare Workers + Durable Objects).
 *
 * Cycle d'une room :
 *   lobby → playing → ended → (host restart) → lobby
 *
 * Règles :
 * - Tout le monde voit la même grille et le même joueur proposé.
 * - Timer authoritatif côté serveur (10s). Si tous ont placé/passé avant,
 *   on avance plus vite.
 * - Le booléen `wasCorrect` est masqué pendant la partie (rouge révélé
 *   uniquement à la fin) → comme la version solo.
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
  cellId: string | null; // null = skip / timeout
  wasCorrect: boolean | null;
  turnIndex: number;
};

type RoomState = {
  status: Status;
  hostId: string | null;
  players: Record<string, Player>;
  game: Game | null;
  turnIndex: number;
  turnEndsAt: number; // ms epoch
  placements: Record<string, Placement[]>; // playerId → liste chronologique
};

// ─── Vue par joueur (cache wasCorrect pendant la partie) ─────────────────

type PublicCellState = {
  status: "empty" | "filled" | "wrong";
  playerName: string | null;
  turnIndex: number | null;
};

type LeaderboardEntry = {
  id: string;
  name: string;
  placed: number;     // cases posées (correctes + erronées)
  correct: number;    // visible seulement quand status === "ended"
  score: number;      // visible seulement quand status === "ended"
};

function viewForRecipient(state: RoomState, recipientId: string) {
  const reveal = state.status === "ended";
  const cells: Record<string, PublicCellState> = {};
  if (state.game) {
    for (const c of state.game.cells) {
      cells[c.id] = { status: "empty", playerName: null, turnIndex: null };
    }
  }

  // Reconstitue l'état de la grille du recipient
  const myPlacements = state.placements[recipientId] || [];
  for (const p of myPlacements) {
    if (p.cellId === null) continue;
    const visualStatus =
      reveal && p.wasCorrect === false ? "wrong" : "filled";
    cells[p.cellId] = {
      status: visualStatus,
      playerName: state.game?.sequence[p.turnIndex]?.name ?? null,
      turnIndex: p.turnIndex,
    };
  }

  // Leaderboard : nombre de placements (visible toujours), score (final only)
  const leaderboard: LeaderboardEntry[] = Object.values(state.players).map(
    (p) => {
      const placements = state.placements[p.id] || [];
      const placed = placements.filter((pl) => pl.cellId !== null).length;
      const correct = placements.filter((pl) => pl.wasCorrect === true).length;
      return {
        id: p.id,
        name: p.name,
        placed,
        correct: reveal ? correct : 0,
        score: reveal ? correct * POOL.rules.pointsPerCell : 0,
      };
    },
  );

  // Le client doit savoir s'il a déjà agi sur le tour courant (lock UI)
  const actedThisTurn = myPlacements.some(
    (p) => p.turnIndex === state.turnIndex,
  );

  return {
    status: state.status,
    hostId: state.hostId,
    selfId: recipientId,
    isHost: state.hostId === recipientId,
    players: Object.values(state.players).sort(
      (a, b) => a.joinedAt - b.joinedAt,
    ),
    cells: state.game?.cells ?? [],
    cellStates: cells,
    sequenceLength: state.game?.sequence.length ?? 0,
    currentPlayer:
      state.game && state.status === "playing"
        ? state.game.sequence[state.turnIndex] ?? null
        : null,
    turnIndex: state.turnIndex,
    turnEndsAt: state.turnEndsAt,
    serverTime: Date.now(),
    actedThisTurn,
    leaderboard,
    rules: POOL.rules,
  };
}

// ─── Server ──────────────────────────────────────────────────────────────

export default class NbaBingoServer implements Party.Server {
  state: RoomState;
  turnTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(readonly room: Party.Room) {
    this.state = {
      status: "lobby",
      hostId: null,
      players: {},
      game: null,
      turnIndex: 0,
      turnEndsAt: 0,
      placements: {},
    };
  }

  // ─── Lifecycle ─────────────────────────────────────────────────────────

  onConnect(conn: Party.Connection) {
    this.sendStateTo(conn);
  }

  onClose(conn: Party.Connection) {
    this.removePlayer(conn.id);
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
        this.handleJoin(sender, sanitizeName(msg.name));
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

  // ─── Handlers ──────────────────────────────────────────────────────────

  handleJoin(conn: Party.Connection, name: string) {
    if (!name) return;
    if (!this.state.players[conn.id]) {
      this.state.players[conn.id] = {
        id: conn.id,
        name,
        joinedAt: Date.now(),
      };
      this.state.placements[conn.id] = [];
      if (!this.state.hostId) this.state.hostId = conn.id;
    } else {
      // Rename d'un participant existant (rare, mais safe)
      this.state.players[conn.id].name = name;
    }
    this.broadcast();
  }

  removePlayer(id: string) {
    if (!this.state.players[id]) return;
    delete this.state.players[id];
    delete this.state.placements[id];
    if (this.state.hostId === id) {
      const remaining = Object.keys(this.state.players);
      this.state.hostId = remaining[0] ?? null;
    }
    if (Object.keys(this.state.players).length === 0) {
      this.resetToLobby();
    }
    this.broadcast();
  }

  handleStart(sender: Party.Connection) {
    if (sender.id !== this.state.hostId) return;
    if (this.state.status !== "lobby") return;
    if (Object.keys(this.state.players).length === 0) return;

    if (POOL.games.length === 0) return;
    const pick = POOL.games[Math.floor(Math.random() * POOL.games.length)];
    this.state.game = pick;
    this.state.status = "playing";
    this.state.turnIndex = 0;
    for (const id of Object.keys(this.state.placements)) {
      this.state.placements[id] = [];
    }
    this.beginTurn();
  }

  handlePlace(sender: Party.Connection, cellId: string) {
    if (this.state.status !== "playing" || !this.state.game) return;
    const playerId = sender.id;
    if (!this.state.players[playerId]) return;

    const placements = this.state.placements[playerId] || [];
    if (placements.some((p) => p.turnIndex === this.state.turnIndex)) return;
    if (placements.some((p) => p.cellId === cellId)) return;

    const seq = this.state.game.sequence[this.state.turnIndex];
    if (!seq) return;
    const wasCorrect = seq.validCellIds.includes(cellId);
    placements.push({
      cellId,
      wasCorrect,
      turnIndex: this.state.turnIndex,
    });
    this.state.placements[playerId] = placements;
    this.broadcast();
    this.maybeAdvanceTurn();
  }

  handleSkip(sender: Party.Connection) {
    if (this.state.status !== "playing" || !this.state.game) return;
    const playerId = sender.id;
    if (!this.state.players[playerId]) return;
    const placements = this.state.placements[playerId] || [];
    if (placements.some((p) => p.turnIndex === this.state.turnIndex)) return;
    placements.push({
      cellId: null,
      wasCorrect: null,
      turnIndex: this.state.turnIndex,
    });
    this.state.placements[playerId] = placements;
    this.broadcast();
    this.maybeAdvanceTurn();
  }

  handleRestart(sender: Party.Connection) {
    if (sender.id !== this.state.hostId) return;
    if (this.state.status !== "ended") return;
    this.resetToLobby();
    this.broadcast();
  }

  // ─── Turn loop ─────────────────────────────────────────────────────────

  beginTurn() {
    if (!this.state.game) return;

    if (this.state.turnIndex >= this.state.game.sequence.length) {
      return this.endGame();
    }

    // Si tout le monde a déjà rempli sa grille → fin
    const gridSize = POOL.rules.gridSize;
    const everyoneFull = Object.keys(this.state.players).every((id) => {
      const placed = (this.state.placements[id] || []).filter(
        (p) => p.cellId !== null,
      ).length;
      return placed >= gridSize;
    });
    if (everyoneFull) return this.endGame();

    this.state.turnEndsAt = Date.now() + POOL.rules.secondsPerTurn * 1000;
    this.broadcast();

    this.clearTurnTimer();
    this.turnTimer = setTimeout(
      () => this.advanceTurn(),
      POOL.rules.secondsPerTurn * 1000,
    );
  }

  maybeAdvanceTurn() {
    const turn = this.state.turnIndex;
    const allActed = Object.keys(this.state.players).every((id) =>
      (this.state.placements[id] || []).some((p) => p.turnIndex === turn),
    );
    if (allActed) this.advanceTurn();
  }

  advanceTurn() {
    this.clearTurnTimer();
    this.state.turnIndex += 1;
    this.beginTurn();
  }

  endGame() {
    this.clearTurnTimer();
    this.state.status = "ended";
    this.state.turnEndsAt = 0;
    this.broadcast();
  }

  clearTurnTimer() {
    if (this.turnTimer) {
      clearTimeout(this.turnTimer);
      this.turnTimer = null;
    }
  }

  resetToLobby() {
    this.clearTurnTimer();
    this.state.status = "lobby";
    this.state.game = null;
    this.state.turnIndex = 0;
    this.state.turnEndsAt = 0;
    for (const id of Object.keys(this.state.placements)) {
      this.state.placements[id] = [];
    }
  }

  // ─── Wire ──────────────────────────────────────────────────────────────

  sendStateTo(conn: Party.Connection) {
    const view = viewForRecipient(this.state, conn.id);
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
