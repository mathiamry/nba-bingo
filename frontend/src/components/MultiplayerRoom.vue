<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useMultiplayerStore, ConnStatus } from '../stores/multiplayer.js'
import GridCell from './GridCell.vue'
import PlayerCard from './PlayerCard.vue'
import StatusBanner from './StatusBanner.vue'
import Leaderboard from './Leaderboard.vue'

const props = defineProps({
  roomCode: { type: String, required: true },
})
const emit = defineEmits(['leave'])

const mp = useMultiplayerStore()
const {
  connStatus,
  error,
  serverPhase,
  isHost,
  selfId,
  players,
  leaderboard,
  cells,
  cellStates,
  currentPlayer,
  turnIndex,
  sequenceLength,
  isDone,
  doneCount,
  totalPlayers,
  rules,
  timerProgress,
  myScore,
  won,
  playerName,
  roomState,
  pendingAction,
} = storeToRefs(mp)

const timeLeftSeconds = computed(() => Math.max(0, mp.timeLeftMs / 1000))

const inputName = ref(playerName.value || '')
const showCopied = ref(false)

onMounted(() => {
  if (mp.playerName) {
    mp.connect(props.roomCode)
  }
})

onBeforeUnmount(() => {
  mp.disconnect()
})

function submitName() {
  const v = inputName.value.trim()
  if (!v) return
  mp.setPlayerName(v)
  if (!mp.isConnected) {
    mp.connect(props.roomCode)
  }
}

function leave() {
  mp.disconnect()
  emit('leave')
}

async function copyLink() {
  const url = `${window.location.origin}${window.location.pathname}#/r/${props.roomCode}`
  try {
    await navigator.clipboard.writeText(url)
    showCopied.value = true
    setTimeout(() => (showCopied.value = false), 1500)
  } catch {
    // pas grave, le user verra le code à recopier à la main
  }
}

const reveal = computed(() => serverPhase.value === 'ended')

const placedCount = computed(() => {
  const me = leaderboard.value.find((p) => p.id === selfId.value)
  return me?.placed ?? 0
})

const cellGridDisabled = computed(
  () =>
    serverPhase.value !== 'playing' ||
    isDone.value ||
    pendingAction.value ||
    !currentPlayer.value,
)

// Erreur "dure" qui mérite le bandeau rouge bloquant :
// - vraie erreur réseau
// - close prolongé sans aucun state reçu (la connexion n'a jamais abouti)
const fatalError = computed(() => {
  if (connStatus.value === ConnStatus.ERROR) return true
  if (connStatus.value === ConnStatus.CLOSED && !roomState.value) return true
  return false
})

// Petit badge "reconnexion…" pour les coupures transitoires (partysocket
// reconnecte automatiquement, on garde le dernier state pour ne pas
// flasher la UI).
const reconnecting = computed(
  () => connStatus.value === ConnStatus.CLOSED && !!roomState.value,
)
</script>

<template>
  <main class="w-full max-w-md px-3 mt-4 flex flex-col gap-4">
    <!-- Bandeau room -->
    <div class="bg-bingo-banner/40 border border-white/10 rounded-xl px-3 py-2 flex items-center gap-2">
      <button
        class="text-white/60 hover:text-white text-lg leading-none px-1"
        title="Quitter la room"
        @click="leave"
      >←</button>
      <div class="flex-1 min-w-0">
        <div class="text-[10px] uppercase tracking-widest opacity-60">Code de la room</div>
        <div class="font-mono font-bold tracking-widest text-base truncate">{{ roomCode }}</div>
      </div>
      <button
        class="text-xs px-3 py-1.5 rounded-md bg-white/10 hover:bg-white/20 uppercase tracking-wider font-semibold"
        @click="copyLink"
      >
        {{ showCopied ? 'Copié ✓' : 'Lien' }}
      </button>
    </div>

    <!-- Saisie du nom si vide -->
    <div v-if="!playerName" class="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col gap-2">
      <label class="text-xs uppercase tracking-widest opacity-60">Ton prénom</label>
      <div class="flex gap-2">
        <input
          v-model="inputName"
          type="text"
          maxlength="24"
          placeholder="Ex. Mathia"
          class="flex-1 bg-white/10 border border-white/20 rounded-lg px-3 py-2 focus:outline-none focus:border-bingo-cell"
          @keydown.enter="submitName"
        />
        <button
          class="bg-bingo-cell text-bingo-textDark font-bold uppercase tracking-wider px-4 rounded-lg hover:brightness-110 disabled:opacity-40"
          :disabled="!inputName.trim()"
          @click="submitName"
        >
          Rejoindre
        </button>
      </div>
    </div>

    <!-- Erreur dure : bandeau rouge bloquant -->
    <div
      v-if="fatalError"
      class="bg-bingo-cellLocked/20 border border-bingo-cellLocked rounded-xl p-3 text-sm flex items-center justify-between gap-3"
    >
      <span>{{ error || 'Connexion fermée.' }}</span>
      <button
        class="text-xs px-3 py-1.5 rounded-md bg-white/10 hover:bg-white/20 uppercase tracking-wider font-semibold"
        @click="mp.connect(props.roomCode)"
      >Réessayer</button>
    </div>

    <!-- Coupure transitoire : petit badge non bloquant -->
    <div
      v-else-if="reconnecting"
      class="bg-yellow-400/15 border border-yellow-400/40 rounded-lg px-3 py-1.5 text-xs flex items-center gap-2"
    >
      <span class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
      <span class="opacity-80">Reconnexion…</span>
    </div>

    <div
      v-else-if="connStatus === 'connecting' && playerName"
      class="text-center opacity-60 py-4 text-sm"
    >Connexion à la room…</div>

    <!-- LOBBY -->
    <template v-if="serverPhase === 'lobby' && connStatus === 'connected'">
      <section class="bg-white/5 border border-white/10 rounded-xl p-4">
        <div class="text-xs uppercase tracking-widest opacity-60 mb-2">
          Participants ({{ players.length }})
        </div>
        <ul class="space-y-1.5">
          <li v-for="p in players" :key="p.id" class="flex items-center gap-2 text-sm">
            <span class="w-2 h-2 rounded-full bg-bingo-cell"></span>
            <span class="font-semibold truncate">{{ p.name }}</span>
            <span v-if="p.id === selfId" class="opacity-50 text-xs">(toi)</span>
            <span v-if="p.id === mp.roomState?.hostId" class="ml-auto text-[10px] uppercase tracking-wider bg-bingo-cell/20 text-bingo-cell px-1.5 py-0.5 rounded">Host</span>
          </li>
        </ul>
      </section>

      <button
        v-if="isHost"
        class="w-full bg-bingo-cell text-bingo-textDark font-extrabold uppercase tracking-widest py-3 rounded-xl hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
        :disabled="players.length === 0"
        @click="mp.start()"
      >Lancer la partie</button>
      <p v-else class="text-center text-sm opacity-60 py-2">
        En attente du host pour lancer…
      </p>
    </template>

    <!-- PLAYING -->
    <template v-if="serverPhase === 'playing'">
      <StatusBanner
        :ended="false"
        :won="false"
        :placed-count="placedCount"
        :total="rules.gridSize"
      />

      <!-- Joueur courant + timer perso (caché si on a fini) -->
      <PlayerCard
        v-if="!isDone"
        :player="currentPlayer"
        :turn-index="turnIndex"
        :total-turns="sequenceLength"
        :time-left="timeLeftSeconds"
        :timer-progress="timerProgress"
        @skip="mp.skip()"
      />

      <!-- Tu as fini, on attend les autres -->
      <div
        v-else
        class="bg-bingo-cell/10 border border-bingo-cell/40 rounded-2xl p-4 text-center"
      >
        <div class="text-bingo-cell font-extrabold uppercase tracking-widest text-sm mb-1">
          Tu as terminé !
        </div>
        <div class="text-xs opacity-70">
          En attente des autres joueurs… ({{ doneCount }} / {{ totalPlayers }} ont fini)
        </div>
      </div>

      <div v-if="cells.length === 16" class="grid grid-cols-4 grid-rows-4 gap-2 sm:gap-3 [grid-auto-rows:minmax(0,1fr)] aspect-[4/5]">
        <GridCell
          v-for="cell in cells"
          :key="cell.id"
          :cell="cell"
          :state="cellStates[cell.id] || { status: 'empty', playerName: null, wasCorrect: null }"
          :reveal-errors="false"
          :disabled="cellGridDisabled"
          @click="(id) => mp.place(id)"
        />
      </div>

      <Leaderboard
        :entries="leaderboard"
        :self-id="selfId"
        :reveal="false"
        :total="rules.gridSize"
      />
    </template>

    <!-- ENDED -->
    <template v-if="serverPhase === 'ended'">
      <StatusBanner
        :ended="true"
        :won="won"
        :placed-count="placedCount"
        :total="rules.gridSize"
        @restart="isHost && mp.restart()"
      />

      <Leaderboard
        :entries="leaderboard"
        :self-id="selfId"
        :reveal="true"
        :total="rules.gridSize"
      />

      <div v-if="cells.length === 16" class="grid grid-cols-4 grid-rows-4 gap-2 sm:gap-3 [grid-auto-rows:minmax(0,1fr)] aspect-[4/5]">
        <GridCell
          v-for="cell in cells"
          :key="cell.id"
          :cell="cell"
          :state="cellStates[cell.id] || { status: 'empty', playerName: null, wasCorrect: null }"
          :reveal-errors="true"
          :disabled="true"
          @click="() => {}"
        />
      </div>

      <button
        v-if="isHost"
        class="w-full bg-bingo-cell text-bingo-textDark font-extrabold uppercase tracking-widest py-3 rounded-xl hover:brightness-110"
        @click="mp.restart()"
      >Rejouer (même room)</button>
      <p v-else class="text-center text-sm opacity-60">En attente du host pour rejouer…</p>
    </template>
  </main>
</template>
