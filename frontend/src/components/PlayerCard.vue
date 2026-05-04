<script setup>
import { computed } from 'vue'

const props = defineProps({
  player: { type: Object, default: null },
  turnIndex: { type: Number, default: 0 },
  totalTurns: { type: Number, default: 0 },
  timeLeft: { type: Number, default: 0 },
  timerProgress: { type: Number, default: 1 },
})

defineEmits(['skip'])

const initials = computed(() => {
  if (!props.player) return '?'
  return props.player.name
    .split(' ')
    .map((s) => s[0])
    .filter(Boolean)
    .join('')
    .slice(0, 2)
    .toUpperCase()
})

// Cercle de progression — circonférence d'un cercle r=28
const RADIUS = 28
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

const dashOffset = computed(() => CIRCUMFERENCE * (1 - props.timerProgress))

const ringColor = computed(() => {
  if (props.timeLeft <= 3) return '#e85f5f'
  if (props.timeLeft <= 6) return '#f5c452'
  return '#d3f04a'
})
</script>

<template>
  <div class="bg-white/5 backdrop-blur-sm rounded-2xl p-4 border border-white/10 flex items-center gap-4">
    <div class="relative w-20 h-20 shrink-0">
      <svg class="absolute inset-0 -rotate-90" viewBox="0 0 64 64" aria-hidden="true">
        <circle cx="32" cy="32" :r="RADIUS" stroke="rgba(255,255,255,0.1)" stroke-width="4" fill="none" />
        <circle
          cx="32"
          cy="32"
          :r="RADIUS"
          :stroke="ringColor"
          stroke-width="4"
          fill="none"
          stroke-linecap="round"
          :stroke-dasharray="CIRCUMFERENCE"
          :stroke-dashoffset="dashOffset"
          style="transition: stroke-dashoffset 0.1s linear, stroke 0.3s"
        />
      </svg>
      <div class="absolute inset-2 rounded-full bg-bingo-cell flex items-center justify-center text-bingo-textDark text-xl font-bold">
        {{ initials }}
      </div>
    </div>

    <div class="flex-1 min-w-0">
      <div class="flex items-center justify-between">
        <div class="text-xs uppercase tracking-widest opacity-60">Joueur à placer</div>
        <div v-if="player" class="text-xs font-bold tabular-nums" :style="{ color: ringColor }">
          {{ Math.ceil(timeLeft) }}s
        </div>
      </div>
      <div
        class="font-bold leading-tight break-words"
        :class="player && player.name.length > 18 ? 'text-base sm:text-lg' : 'text-lg sm:text-xl'"
      >
        {{ player ? player.name : 'En attente…' }}
      </div>
      <div class="text-xs opacity-60 mt-1">
        Tour {{ turnIndex + 1 }} / {{ totalTurns }}
      </div>
    </div>

    <button
      class="text-xs px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors uppercase tracking-wider font-semibold disabled:opacity-30 disabled:cursor-not-allowed"
      :disabled="!player"
      @click="$emit('skip')"
    >
      Passer
    </button>
  </div>
</template>
