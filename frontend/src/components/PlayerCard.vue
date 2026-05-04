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

// Split name into first / last parts
const firstName = computed(() => {
  if (!props.player) return ''
  const parts = props.player.name.trim().split(/\s+/)
  return parts.slice(0, -1).join(' ')
})

const lastName = computed(() => {
  if (!props.player) return ''
  const parts = props.player.name.trim().split(/\s+/)
  return parts[parts.length - 1]
})

// SVG ring
const RADIUS = 28
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const dashOffset = computed(() => CIRCUMFERENCE * (1 - props.timerProgress))

const ringColor = computed(() => {
  if (props.timeLeft <= 3) return '#e85f5f'
  if (props.timeLeft <= 6) return '#f5c452'
  return '#22c55e'
})

// "X REMAINING" — never negative
const remaining = computed(() => Math.max(0, props.totalTurns - props.turnIndex - 1))

const timeDisplay = computed(() => Math.ceil(props.timeLeft))
</script>

<template>
  <div
    class="w-full flex items-center gap-4 sm:gap-5 px-4 py-3 sm:px-5 sm:py-4 rounded-2xl mx-1"
    style="background: linear-gradient(135deg, #3b3aff 0%, #5554ff 60%, #4443ef 100%);"
  >

    <!-- Timer circle: white disc + colour SVG arc -->
    <div class="relative shrink-0 w-[64px] h-[64px] sm:w-[72px] sm:h-[72px]">
      <!-- Track ring (dim white) -->
      <svg
        class="absolute inset-0 -rotate-90 w-full h-full"
        viewBox="0 0 72 72"
        aria-hidden="true"
      >
        <circle
          cx="36" cy="36" :r="RADIUS"
          stroke="rgba(255,255,255,0.18)" stroke-width="5" fill="none"
        />
        <circle
          cx="36" cy="36" :r="RADIUS"
          :stroke="ringColor"
          stroke-width="5"
          fill="none"
          stroke-linecap="round"
          :stroke-dasharray="CIRCUMFERENCE"
          :stroke-dashoffset="dashOffset"
          style="transition: stroke-dashoffset 0.1s linear, stroke 0.3s"
        />
      </svg>
      <!-- White disc — ring glow + inner shadow for depth -->
      <div
        class="absolute rounded-full bg-white flex items-center justify-center ring-2 ring-white/30 shadow-inner"
        style="inset: 7px;"
      >
        <span class="text-2xl sm:text-3xl font-extrabold text-gray-900 tabular-nums leading-none">
          {{ player ? timeDisplay : '--' }}
        </span>
      </div>
    </div>

    <!-- Player name: first name small on top, last name large below -->
    <div class="flex-1 min-w-0 flex flex-col gap-0.5">
      <template v-if="player">
        <span
          v-if="firstName"
          class="text-[11px] sm:text-xs uppercase tracking-[0.16em] font-semibold opacity-70 leading-none"
        >{{ firstName }}</span>
        <span
          class="text-2xl sm:text-3xl font-extrabold uppercase leading-tight break-words tracking-[0.04em]"
          style="text-shadow: 0 1px 4px rgba(0,0,0,0.35)"
        >{{ lastName }}</span>
      </template>
      <span
        v-else
        class="text-xl sm:text-2xl font-extrabold uppercase opacity-60 leading-tight"
      >EN ATTENTE</span>
    </div>

    <!-- Skip + remaining count — right-aligned tight block -->
    <div class="flex flex-col items-end shrink-0 gap-1">
      <button
        class="text-sm sm:text-base font-extrabold uppercase tracking-widest leading-none disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-80 transition-opacity"
        :disabled="!player"
        @click="$emit('skip')"
      >SKIP ▶︎</button>
      <span class="text-[11px] sm:text-xs font-semibold uppercase tracking-[0.12em] opacity-55 tabular-nums leading-none">
        {{ remaining }}&nbsp;LEFT
      </span>
    </div>

  </div>
</template>
