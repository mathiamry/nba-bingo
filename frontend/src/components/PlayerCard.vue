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
    .split(/[\s-]+/)
    .map((s) => s[0])
    .filter(Boolean)
    .join('')
    .slice(0, 2)
    .toUpperCase()
})

const RADIUS = 30
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const dashOffset = computed(() => CIRCUMFERENCE * (1 - props.timerProgress))

const ringColor = computed(() => {
  if (props.timeLeft <= 3) return '#e85f5f'
  if (props.timeLeft <= 6) return '#f5c452'
  return '#d3f04a'
})

const remaining = computed(() => Math.max(0, props.totalTurns - props.turnIndex))
</script>

<template>
  <div
    class="bg-white/[0.04] backdrop-blur-sm rounded-2xl p-4 sm:p-5 border border-white/10 flex items-center gap-4 sm:gap-5"
  >
    <!-- Avatar + ring de timer -->
    <div class="relative w-[72px] h-[72px] sm:w-20 sm:h-20 shrink-0">
      <svg class="absolute inset-0 -rotate-90" viewBox="0 0 72 72" aria-hidden="true">
        <circle
          cx="36" cy="36" :r="RADIUS"
          stroke="rgba(255,255,255,0.10)" stroke-width="4" fill="none"
        />
        <circle
          cx="36" cy="36" :r="RADIUS"
          :stroke="ringColor" stroke-width="4" fill="none"
          stroke-linecap="round"
          :stroke-dasharray="CIRCUMFERENCE"
          :stroke-dashoffset="dashOffset"
          style="transition: stroke-dashoffset 0.1s linear, stroke 0.3s"
        />
      </svg>
      <div
        class="absolute inset-2 rounded-full bg-bingo-cell flex items-center justify-center text-bingo-textDark text-xl sm:text-2xl font-extrabold"
      >{{ initials }}</div>
    </div>

    <!-- Texte central -->
    <div class="flex-1 min-w-0 flex flex-col gap-0.5">
      <div class="flex items-baseline gap-2 flex-wrap">
        <span class="text-[10px] sm:text-xs uppercase tracking-[0.18em] opacity-60 font-semibold">
          Joueur à placer
        </span>
        <span
          v-if="player"
          class="text-xs sm:text-sm font-bold tabular-nums"
          :style="{ color: ringColor }"
        >{{ Math.ceil(timeLeft) }}s</span>
      </div>
      <div
        class="font-extrabold leading-tight break-words"
        :class="player && player.name.length > 18 ? 'text-lg sm:text-xl' : 'text-xl sm:text-2xl'"
      >
        {{ player ? player.name : 'En attente…' }}
      </div>
      <div class="text-[11px] sm:text-xs opacity-60 mt-0.5 uppercase tracking-wider">
        Tour {{ turnIndex + 1 }} / {{ totalTurns }}<span v-if="player"> · {{ remaining }} restants</span>
      </div>
    </div>

    <!-- Bouton Skip à la Football Bingo : texte + chevron, sans fioritures -->
    <button
      class="flex items-center gap-1 text-xs sm:text-sm uppercase tracking-widest font-extrabold opacity-90 hover:opacity-100 disabled:opacity-30 disabled:cursor-not-allowed shrink-0 px-1"
      :disabled="!player"
      @click="$emit('skip')"
    >
      Skip
      <span class="text-base">▶︎</span>
    </button>
  </div>
</template>
