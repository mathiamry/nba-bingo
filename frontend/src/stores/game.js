import { defineStore } from 'pinia'

const CELL_STATUS = {
  EMPTY: 'empty',
  FILLED: 'filled', // une case placée — correcte OU incorrecte (révélé en fin de partie)
}

const GAME_STATUS = {
  LOADING: 'loading',
  PLAYING: 'playing',
  ENDED: 'ended',
}

const TURN_OUTCOME = {
  CORRECT: 'correct',
  WRONG: 'wrong',
  SKIPPED: 'skipped',
  TIMEOUT: 'timeout',
}

const TICK_MS = 100
const NAME_KEY = 'nbaBingoPlayerName'

let timerHandle = null

function loadStoredName() {
  try {
    return localStorage.getItem(NAME_KEY) || ''
  } catch {
    return ''
  }
}

export const useGameStore = defineStore('game', {
  state: () => ({
    cells: [],
    sequence: [],
    rules: { maxStrikes: 2, gridSize: 16, totalPerfectScore: 60, pointsPerCell: 3.75, secondsPerTurn: 10 },
    turnIndex: 0,
    strikes: 0,
    status: GAME_STATUS.LOADING,
    cellStates: {}, // cellId -> { status, playerName, wasCorrect }
    history: [],
    timeLeftMs: 0,
    error: null,
    playerName: loadStoredName(),
  }),

  getters: {
    currentPlayer(state) {
      if (state.turnIndex >= state.sequence.length) return null
      return state.sequence[state.turnIndex]
    },
    placedCount(state) {
      return Object.values(state.cellStates).filter(
        (s) => s.status === CELL_STATUS.FILLED,
      ).length
    },
    correctCount(state) {
      return Object.values(state.cellStates).filter(
        (s) => s.status === CELL_STATUS.FILLED && s.wasCorrect === true,
      ).length
    },
    // Alias pour compat — représente les cases correctement validées (utilisé pour le score)
    filledCount(state) {
      return this.correctCount
    },
    score(state) {
      // Somme des points des cases correctement remplies.
      // Chaque case porte sa propre valeur (pondérée par difficulté côté
      // Python), total parfait = 60 pts en entiers.
      return state.cells.reduce((sum, c) => {
        const s = state.cellStates[c.id]
        return s && s.status === CELL_STATUS.FILLED && s.wasCorrect === true
          ? sum + (c.points || 0)
          : sum
      }, 0)
    },
    isPlaying(state) {
      return state.status === GAME_STATUS.PLAYING
    },
    isEnded(state) {
      return state.status === GAME_STATUS.ENDED
    },
    timeLeftSeconds(state) {
      return Math.max(0, state.timeLeftMs / 1000)
    },
    timerProgress(state) {
      const total = state.rules.secondsPerTurn * 1000
      if (total === 0) return 0
      return Math.max(0, Math.min(1, state.timeLeftMs / total))
    },
    won(state) {
      return state.status === GAME_STATUS.ENDED && this.correctCount === state.rules.gridSize
    },
  },

  actions: {
    async loadGame() {
      this._stopTimer()
      this.status = GAME_STATUS.LOADING
      this.error = null
      try {
        const res = await fetch('/game.json')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        const games = data.games || []
        if (!games.length) throw new Error('Aucune partie disponible.')
        const pick = games[Math.floor(Math.random() * games.length)]
        this.cells = pick.cells
        this.sequence = pick.sequence
        this.rules = { ...this.rules, ...data.rules }
        this.turnIndex = 0
        this.strikes = 0
        this.history = []
        this.cellStates = Object.fromEntries(
          this.cells.map((c) => [c.id, { status: CELL_STATUS.EMPTY, playerName: null, wasCorrect: null }]),
        )
        this.status = GAME_STATUS.PLAYING
        this._startTimer()
      } catch (err) {
        this.error = err.message
        this.status = GAME_STATUS.ENDED
      }
    },

    placePlayer(cellId) {
      if (!this.isPlaying) return
      const cell = this.cellStates[cellId]
      if (!cell || cell.status !== CELL_STATUS.EMPTY) return

      const player = this.currentPlayer
      if (!player) return

      const isValid = player.validCellIds.includes(cellId)
      // Quel que soit le résultat, la case est posée et figée (verte pendant la partie).
      this.cellStates[cellId] = {
        status: CELL_STATUS.FILLED,
        playerName: player.name,
        wasCorrect: isValid,
      }
      if (!isValid) this.strikes += 1
      this.history.push({
        playerName: player.name,
        cellId,
        cellLabel: this._labelOf(cellId),
        outcome: isValid ? TURN_OUTCOME.CORRECT : TURN_OUTCOME.WRONG,
      })
      this._advance()
    },

    skipPlayer() {
      if (!this.isPlaying) return
      const player = this.currentPlayer
      if (player) {
        this.history.push({
          playerName: player.name,
          cellId: null,
          cellLabel: null,
          outcome: TURN_OUTCOME.SKIPPED,
        })
      }
      this._advance()
    },

    _onTimeout() {
      if (!this.isPlaying) return
      const player = this.currentPlayer
      if (player) {
        this.history.push({
          playerName: player.name,
          cellId: null,
          cellLabel: null,
          outcome: TURN_OUTCOME.TIMEOUT,
        })
      }
      this._advance()
    },

    _advance() {
      this.turnIndex += 1
      this._checkEnd()
      if (this.isPlaying) {
        this._startTimer()
      } else {
        this._stopTimer()
      }
    },

    _checkEnd() {
      // La partie se termine quand toutes les cases sont posées (correctes OU non),
      // ou quand la séquence est épuisée. Les strikes ne stoppent jamais.
      if (this.placedCount >= this.rules.gridSize) {
        this.status = GAME_STATUS.ENDED
        return
      }
      if (this.turnIndex >= this.sequence.length) {
        this.status = GAME_STATUS.ENDED
      }
    },

    _startTimer() {
      this._stopTimer()
      this.timeLeftMs = this.rules.secondsPerTurn * 1000
      timerHandle = setInterval(() => {
        this.timeLeftMs -= TICK_MS
        if (this.timeLeftMs <= 0) {
          this._stopTimer()
          this._onTimeout()
        }
      }, TICK_MS)
    },

    _stopTimer() {
      if (timerHandle) {
        clearInterval(timerHandle)
        timerHandle = null
      }
    },

    _labelOf(cellId) {
      const c = this.cells.find((x) => x.id === cellId)
      return c ? c.label : cellId
    },

    setPlayerName(name) {
      const trimmed = (name || '').trim()
      this.playerName = trimmed
      try {
        if (trimmed) localStorage.setItem(NAME_KEY, trimmed)
        else localStorage.removeItem(NAME_KEY)
      } catch {
        // localStorage indisponible — on ignore, le nom reste en mémoire
      }
    },

    reset() {
      this.loadGame()
    },
  },
})

export { CELL_STATUS, GAME_STATUS, TURN_OUTCOME }
