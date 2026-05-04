import { defineStore } from 'pinia'
import PartySocket from 'partysocket'

// En prod, le frontend est servi par PartyKit lui-même → on tape la même
// origine via window.location.host. En dev local, l'override va sur le
// dev server PartyKit (127.0.0.1:1999) via .env.development.local.
const HOST =
  import.meta.env.VITE_PARTYKIT_HOST ||
  (typeof window !== 'undefined' ? window.location.host : '127.0.0.1:1999')
const NAME_KEY = 'nbaBingoPlayerName'
const SESSION_KEY = 'nbaBingoSessionId'

function loadOrCreateSessionId() {
  try {
    let id = localStorage.getItem(SESSION_KEY)
    if (!id) {
      id =
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : 's_' + Math.random().toString(36).slice(2) + Date.now().toString(36)
      localStorage.setItem(SESSION_KEY, id)
    }
    return id
  } catch {
    return 's_' + Math.random().toString(36).slice(2)
  }
}

const SESSION_ID = loadOrCreateSessionId()

const ConnStatus = {
  IDLE: 'idle',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  CLOSED: 'closed',
  ERROR: 'error',
}

let socket = null
let abortController = null
let tickerHandle = null

function loadStoredName() {
  try {
    return localStorage.getItem(NAME_KEY) || ''
  } catch {
    return ''
  }
}

export const useMultiplayerStore = defineStore('multiplayer', {
  state: () => ({
    roomCode: null,
    playerName: loadStoredName(),
    roomState: null,
    connStatus: ConnStatus.IDLE,
    error: null,
    nowMs: Date.now(),
    pendingAction: false,
  }),

  getters: {
    isConnected: (s) => s.connStatus === ConnStatus.CONNECTED,
    selfId: (s) => s.roomState?.selfId ?? null,
    isHost: (s) => s.roomState?.isHost === true,
    serverPhase: (s) => s.roomState?.status ?? 'lobby',
    players: (s) => s.roomState?.players ?? [],
    leaderboard: (s) => s.roomState?.leaderboard ?? [],
    cells: (s) => s.roomState?.cells ?? [],
    cellStates: (s) => s.roomState?.cellStates ?? {},
    currentPlayer: (s) => s.roomState?.currentPlayer ?? null,
    turnIndex: (s) => s.roomState?.turnIndex ?? 0,
    sequenceLength: (s) => s.roomState?.sequenceLength ?? 0,
    isDone: (s) => s.roomState?.isDone === true,
    doneCount: (s) => s.roomState?.doneCount ?? 0,
    totalPlayers: (s) => s.roomState?.totalPlayers ?? 0,
    rules: (s) =>
      s.roomState?.rules ?? {
        secondsPerTurn: 10,
        gridSize: 16,
        totalPerfectScore: 60,
        pointsPerCell: 3.75,
        maxStrikes: 2,
      },
    timeLeftMs: (s) => {
      if (!s.roomState || s.roomState.status !== 'playing') return 0
      return Math.max(0, (s.roomState.turnEndsAt || 0) - s.nowMs)
    },
    timerProgress(state) {
      const total = (this.rules.secondsPerTurn || 10) * 1000
      if (total === 0) return 0
      return Math.max(0, Math.min(1, this.timeLeftMs / total))
    },
    won(state) {
      if (this.serverPhase !== 'ended') return false
      const me = this.leaderboard.find((p) => p.id === this.selfId)
      return !!me && me.correct === this.rules.gridSize
    },
    myScore(state) {
      const me = this.leaderboard.find((p) => p.id === this.selfId)
      return me?.score ?? 0
    },
  },

  actions: {
    setPlayerName(name) {
      const trimmed = (name || '').trim().slice(0, 24)
      this.playerName = trimmed
      try {
        if (trimmed) localStorage.setItem(NAME_KEY, trimmed)
        else localStorage.removeItem(NAME_KEY)
      } catch {
        // localStorage indisponible — on garde en mémoire seulement
      }
      // Si on est déjà connecté, renvoie un join pour mettre à jour le nom côté serveur
      if (this.isConnected && trimmed) {
        this._send({ type: 'join', name: trimmed, sessionId: SESSION_ID })
      }
    },

    connect(roomCode) {
      const code = (roomCode || '').toUpperCase().trim()
      if (!code) return
      if (!this.playerName) {
        this.error = 'Choisis un nom avant de rejoindre.'
        return
      }
      this.disconnect()
      this.error = null
      this.roomCode = code
      this.connStatus = ConnStatus.CONNECTING

      abortController = new AbortController()
      const { signal } = abortController

      socket = new PartySocket({
        host: HOST,
        room: code,
      })

      socket.addEventListener('open', () => {
        this.connStatus = ConnStatus.CONNECTED
        this._send({ type: 'join', name: this.playerName, sessionId: SESSION_ID })
        this._startTicker()
      }, { signal })
      socket.addEventListener('message', (event) => {
        let msg
        try {
          msg = JSON.parse(event.data)
        } catch {
          return
        }
        if (msg.type === 'state') {
          this.roomState = msg.state
          // Tout state reçu = le serveur a traité notre dernière action
          this.pendingAction = false
        }
      }, { signal })
      socket.addEventListener('close', () => {
        // partysocket reconnecte automatiquement ; on tombe en CLOSED
        // mais on garde roomState pour ne pas casser la UI le temps de
        // la reco. L'event 'open' suivant remettra à CONNECTED.
        this.connStatus = ConnStatus.CLOSED
        this._stopTicker()
      }, { signal })
      socket.addEventListener('error', () => {
        this.connStatus = ConnStatus.ERROR
        this.error = `Connexion impossible à ${HOST}`
        this._stopTicker()
      }, { signal })
    },

    disconnect() {
      this._stopTicker()
      // AbortController détache TOUS les listeners de l'ancien socket
      // avant qu'on le close — pas de close() qui retombe sur le nouveau.
      if (abortController) {
        abortController.abort()
        abortController = null
      }
      if (socket) {
        try { socket.close() } catch {}
        socket = null
      }
      this.roomState = null
      this.connStatus = ConnStatus.IDLE
      this.roomCode = null
      this.error = null
    },

    start() { this._send({ type: 'start' }) },
    place(cellId) {
      if (this.pendingAction || this.isDone) return
      this.pendingAction = true
      this._send({ type: 'place', cellId })
    },
    skip() {
      if (this.pendingAction || this.isDone) return
      this.pendingAction = true
      this._send({ type: 'skip' })
    },
    restart() {
      this.pendingAction = false
      this._send({ type: 'restart' })
    },

    _send(payload) {
      if (socket && this.isConnected) {
        socket.send(JSON.stringify(payload))
      }
    },

    _startTicker() {
      this._stopTicker()
      tickerHandle = setInterval(() => {
        this.nowMs = Date.now()
      }, 100)
    },

    _stopTicker() {
      if (tickerHandle) {
        clearInterval(tickerHandle)
        tickerHandle = null
      }
    },
  },
})

export { ConnStatus }
