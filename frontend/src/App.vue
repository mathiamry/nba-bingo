<script setup>
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useGameStore } from './stores/game.js'
import GridCell from './components/GridCell.vue'
import PlayerCard from './components/PlayerCard.vue'
import StatusBanner from './components/StatusBanner.vue'
import RecapModal from './components/RecapModal.vue'

const game = useGameStore()
const {
  cells,
  sequence,
  cellStates,
  currentPlayer,
  turnIndex,
  strikes,
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
const showRecap = computed(() => isEnded.value && !modalDismissed.value)

onMounted(() => {
  game.loadGame()
})

onBeforeUnmount(() => {
  game._stopTimer()
})

// Quand une nouvelle partie démarre, on autorise à nouveau le modal pour la prochaine fin.
watch(isPlaying, (playing) => {
  if (playing) modalDismissed.value = false
})

const errorsCount = computed(() => placedCount.value - game.correctCount)

function handleSetName(name) {
  game.setPlayerName(name)
}

function handleRestart() {
  modalDismissed.value = false
  game.reset()
}

function handleCloseRecap() {
  modalDismissed.value = true
}
</script>

<template>
  <div class="min-h-screen flex flex-col items-center pb-10">
    <header class="w-full bg-bingo-header py-5 px-4 text-center">
      <h1 class="text-2xl sm:text-3xl font-extrabold tracking-[0.2em] uppercase">NBA BINGO</h1>
    </header>

    <div class="w-full bg-bingo-banner/80 py-2 text-center text-xs sm:text-sm">
      Place chaque joueur dans une case valide. {{ rules.secondsPerTurn }}s par tour.
    </div>

    <main class="w-full max-w-md px-3 mt-4 flex flex-col gap-4">
      <StatusBanner
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

      <div v-if="cells.length === 16" class="grid grid-cols-4 gap-2">
        <GridCell
          v-for="cell in cells"
          :key="cell.id"
          :cell="cell"
          :state="cellStates[cell.id]"
          :reveal-errors="isEnded"
          :disabled="!isPlaying || !currentPlayer"
          @click="(id) => game.placePlayer(id)"
        />
      </div>

      <div v-if="error" class="bg-bingo-cellLocked/20 border border-bingo-cellLocked rounded-xl p-4 text-sm">
        Impossible de charger la partie : {{ error }}.<br />
        Lance <code class="bg-black/40 px-1 rounded">python3 nba_bingo_grid.py</code> à la racine pour générer
        <code class="bg-black/40 px-1 rounded">frontend/public/game.json</code>.
      </div>
      <div v-else-if="!cells.length" class="text-center opacity-60 py-10">Chargement…</div>
    </main>

    <!-- Récap en popup -->
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
  </div>
</template>
