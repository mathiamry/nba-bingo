<script setup>
import { onMounted, onBeforeUnmount, ref, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useGameStore } from './stores/game.js'
import GridCell from './components/GridCell.vue'
import PlayerCard from './components/PlayerCard.vue'
import StatusBanner from './components/StatusBanner.vue'
import RecapModal from './components/RecapModal.vue'
import HomeScreen from './components/HomeScreen.vue'
import MultiplayerRoom from './components/MultiplayerRoom.vue'

// ─── Hash routing ────────────────────────────────────────────────────────
function parseHash() {
  const raw = window.location.hash.slice(1) || '/'
  if (raw.startsWith('/r/')) {
    const code = raw.slice(3).toUpperCase().replace(/[^A-Z0-9-]/g, '').slice(0, 12)
    if (code) return { name: 'room', code }
  }
  if (raw === '/solo') return { name: 'solo' }
  return { name: 'home' }
}

const route = ref(parseHash())
function onHashChange() {
  route.value = parseHash()
}
window.addEventListener('hashchange', onHashChange)

function navigate(path) {
  window.location.hash = path
}

// ─── Solo mode (lazy-init le store quand on entre en /solo) ─────────────
const game = useGameStore()
const {
  cells,
  sequence,
  cellStates,
  currentPlayer,
  turnIndex,
  rules,
  isPlaying,
  isEnded,
  won,
  score,
  placedCount,
  timeLeftSeconds,
  timerProgress,
  history,
  playerName,
  error,
} = storeToRefs(game)

const modalDismissed = ref(false)
const showRecap = computed(
  () => route.value.name === 'solo' && isEnded.value && !modalDismissed.value,
)

// Charge la partie quand on entre en /solo, et nettoie quand on en sort
watch(
  () => route.value.name,
  (name, prev) => {
    if (name === 'solo' && prev !== 'solo') {
      modalDismissed.value = false
      game.loadGame()
    } else if (prev === 'solo' && name !== 'solo') {
      game._stopTimer()
    }
  },
  { immediate: true },
)

watch(isPlaying, (playing) => {
  if (playing) modalDismissed.value = false
})

const errorsCount = computed(() => placedCount.value - game.correctCount)

function handleSetName(name) { game.setPlayerName(name) }
function handleRestart() { modalDismissed.value = false; game.reset() }
function handleCloseRecap() { modalDismissed.value = true }

onBeforeUnmount(() => {
  window.removeEventListener('hashchange', onHashChange)
  game._stopTimer()
})
</script>

<template>
  <div class="min-h-screen flex flex-col items-center pb-10">
    <!-- Header (toujours visible, clic = retour home) -->
    <header
      class="w-full py-5 px-4 text-center cursor-pointer select-none"
      style="background: linear-gradient(135deg, #3b3aff 0%, #5857ff 55%, #3533d6 100%);"
      @click="navigate('/')"
    >
      <h1
        class="text-2xl sm:text-3xl font-extrabold tracking-[0.25em] uppercase"
        style="text-shadow: 0 2px 8px rgba(0,0,0,0.35);"
      >NBA BINGO</h1>
    </header>

    <!-- HOME -->
    <HomeScreen
      v-if="route.name === 'home'"
      @solo="navigate('/solo')"
      @navigate="navigate"
    />

    <!-- ROOM (multijoueur) -->
    <MultiplayerRoom
      v-else-if="route.name === 'room'"
      :key="route.code"
      :room-code="route.code"
      @leave="navigate('/')"
    />

    <!-- SOLO -->
    <template v-else-if="route.name === 'solo'">
      <div
        class="w-full py-2 text-center text-xs sm:text-sm font-medium tracking-wide border-b border-white/10"
        style="background: linear-gradient(to right, #3b3aff, #3533d6);"
      >
        Mode solo — {{ rules.secondsPerTurn }}s par tour, grille parfaite : {{ rules.totalPerfectScore }} pts.
      </div>

      <main class="w-full max-w-md mt-2 flex flex-col gap-2">
        <!-- StatusBanner edge-to-edge en phase terminée -->
        <StatusBanner
          v-if="isEnded"
          :ended="isEnded"
          :won="won"
          :placed-count="placedCount"
          :total="rules.gridSize"
          @restart="handleRestart"
        />

        <PlayerCard
          v-if="!isEnded"
          :player="currentPlayer"
          :turn-index="turnIndex"
          :total-turns="sequence.length"
          :time-left="timeLeftSeconds"
          :timer-progress="timerProgress"
          @skip="game.skipPlayer()"
        />

        <div
          v-if="cells.length === 16"
          :class="[
            'grid grid-cols-4 grid-rows-4 aspect-square mx-1',
            isEnded
              ? 'gap-2 sm:gap-3'
              : 'rounded-2xl overflow-hidden bg-bingo-cellEmpty',
          ]"
        >
          <GridCell
            v-for="(cell, i) in cells"
            :key="cell.id"
            :cell="cell"
            :state="cellStates[cell.id]"
            :index="i"
            :reveal-errors="isEnded"
            :disabled="!isPlaying || !currentPlayer"
            @click="(id) => game.placePlayer(id)"
          />
        </div>

        <div v-if="error" class="mx-3 bg-bingo-cellLocked/20 border border-bingo-cellLocked rounded-xl p-4 text-sm">
          Impossible de charger la partie : {{ error }}.<br />
          Lance <code class="bg-black/40 px-1 rounded">python3 nba_bingo_grid.py</code> pour générer
          <code class="bg-black/40 px-1 rounded">frontend/public/game.json</code>.
        </div>
        <div v-else-if="!cells.length" class="text-center opacity-60 py-10">Chargement…</div>
      </main>

      <RecapModal
        :show="showRecap"
        :player-name="playerName"
        :score="score"
        :placed="placedCount"
        :total="rules.gridSize"
        :errors-count="errorsCount"
        :won="won"
        @name="handleSetName"
        @restart="handleRestart"
        @close="handleCloseRecap"
      />
    </template>
  </div>
</template>
