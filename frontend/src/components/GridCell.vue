<script setup>
import { computed } from 'vue'
import { CELL_STATUS } from '../stores/game.js'

const props = defineProps({
  cell: { type: Object, required: true },
  state: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
  revealErrors: { type: Boolean, default: false },
})

defineEmits(['click'])

const isEmpty = computed(() => props.state.status === CELL_STATUS.EMPTY)
// "filled" couvre les placements corrects ET les erronés (vert pendant le jeu).
// Le serveur multijoueur envoie status='wrong' uniquement quand on doit révéler.
const isFilled = computed(
  () => props.state.status === 'filled' || props.state.status === 'wrong',
)
// "wrong" n'est révélé que si revealErrors est vrai (en fin de partie).
const showWrong = computed(() => {
  if (!props.revealErrors) return false
  if (props.state.status === 'wrong') return true
  return isFilled.value && props.state.wasCorrect === false
})

const axisIcon = computed(() => {
  switch (props.cell.axis) {
    case 'TEAM': return '🏀'
    case 'NATIONALITY': return '🌍'
    case 'AWARD': return '🏆'
    case 'DRAFT': return '🎯'
    case 'STAT': return '📊'
    case 'CAREER': return '⭐'
    case 'ERA': return '⏳'
    case 'TEAMMATE': return '🤝'
    default: return '•'
  }
})

const cellClasses = computed(() => {
  if (showWrong.value) return 'bg-bingo-cellLocked text-white border-bingo-cellLocked'
  if (isFilled.value) return 'bg-bingo-cell text-bingo-textDark border-bingo-cell'
  return 'bg-bingo-cellEmpty text-white border-white/10 hover:border-bingo-cell/60 hover:bg-white/10'
})

const statusLabel = computed(() => {
  if (showWrong.value) return '✕'
  if (isFilled.value) return '✓'
  return ''
})

const interactable = computed(() => !props.disabled && isEmpty.value)
</script>

<template>
  <button
    :disabled="!interactable"
    :class="['relative aspect-square rounded-lg p-2 transition-all flex flex-col items-center justify-center text-center font-semibold border', cellClasses, interactable ? 'cursor-pointer' : 'cursor-default']"
    @click="$emit('click', cell.id)"
  >
    <span v-if="statusLabel" class="absolute top-1 right-2 text-xs font-bold opacity-80">{{ statusLabel }}</span>

    <div :class="['text-2xl mb-1', isEmpty ? 'opacity-70' : '']" aria-hidden="true">{{ axisIcon }}</div>

    <div :class="['text-[10px] uppercase tracking-wide leading-tight px-1', isEmpty ? 'text-bingo-textMuted' : '']">
      {{ cell.label }}
    </div>

    <div v-if="state.playerName" class="mt-1 text-[9px] font-bold uppercase tracking-wider opacity-90 leading-tight">
      {{ state.playerName }}
    </div>
  </button>
</template>
