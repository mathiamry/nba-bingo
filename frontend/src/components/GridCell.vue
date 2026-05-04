<script setup>
import { computed, ref } from 'vue'
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

// Mapping abbréviation NBA → fichier logo (le zip a quelques quirks).
const LOGO_FILE_MAP = {
  phi: 'phl', // Philadelphia 76ers
  uta: 'uth', // Utah Jazz
}
const LOGO_EXT_MAP = {
  mia: 'gif', // seul fichier en GIF
}

const teamLogoUrl = computed(() => {
  if (props.cell.axis !== 'TEAM') return null
  if (!props.cell.id?.startsWith('team_')) return null
  const abbr = props.cell.id.slice(5).toLowerCase()
  if (abbr.length !== 3) return null
  const file = LOGO_FILE_MAP[abbr] || abbr
  const ext = LOGO_EXT_MAP[abbr] || 'png'
  return `/logos/${file}.${ext}`
})

// Mapping ISO alpha-3 (utilisé dans le dataset) → alpha-2 (flagcdn.com).
const FLAG_ALPHA2 = {
  USA: 'us', FRA: 'fr', CAN: 'ca', SRB: 'rs',
  GRC: 'gr', ESP: 'es', SVN: 'si', DEU: 'de',
  CMR: 'cm', DOM: 'do', TUR: 'tr', FIN: 'fi',
  LTU: 'lt', AUS: 'au', MNE: 'me', HRV: 'hr',
  ARG: 'ar', BIH: 'ba', BRA: 'br', GBR: 'gb',
  ITA: 'it', NGR: 'ng', RUS: 'ru', SWE: 'se',
}

const flagUrl = computed(() => {
  if (props.cell.axis !== 'NATIONALITY') return null
  if (!props.cell.id?.startsWith('nat_')) return null
  const code3 = props.cell.id.slice(4).toUpperCase()
  const code2 = FLAG_ALPHA2[code3]
  if (!code2) return null
  return `https://flagcdn.com/w80/${code2}.png`
})

const imgLoaded = ref(true)
function onImgError() {
  imgLoaded.value = false
}

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

// Tailwind shrink-on-long-labels — évite les overflow tout en restant lisible.
const labelClass = computed(() => {
  const n = (props.cell.label || '').length
  if (n > 22) return 'text-[8px] sm:text-[9px]'
  if (n > 14) return 'text-[9px] sm:text-[10px]'
  return 'text-[10px] sm:text-[11px]'
})

const playerNameClass = computed(() => {
  const n = (props.state.playerName || '').length
  if (n > 18) return 'text-[7px] sm:text-[8px]'
  return 'text-[8px] sm:text-[9px]'
})
</script>

<template>
  <button
    :disabled="!interactable"
    :class="['relative rounded-lg p-1.5 sm:p-2 transition-all flex flex-col items-center justify-center text-center font-semibold border overflow-hidden h-full w-full', cellClasses, interactable ? 'cursor-pointer' : 'cursor-default']"
    @click="$emit('click', cell.id)"
  >
    <span v-if="statusLabel" class="absolute top-1 right-1.5 text-[10px] font-bold opacity-80">{{ statusLabel }}</span>

    <img
      v-if="teamLogoUrl && imgLoaded"
      :src="teamLogoUrl"
      alt=""
      class="w-7 h-7 sm:w-9 sm:h-9 mb-0.5 sm:mb-1 object-contain shrink-0"
      :class="isEmpty ? 'opacity-90' : ''"
      @error="onImgError"
    />
    <img
      v-else-if="flagUrl && imgLoaded"
      :src="flagUrl"
      alt=""
      class="w-7 h-5 sm:w-9 sm:h-6 mb-0.5 sm:mb-1 object-contain rounded-sm shadow-sm shrink-0"
      :class="isEmpty ? 'opacity-90' : ''"
      @error="onImgError"
    />
    <div
      v-else
      :class="['text-xl sm:text-2xl mb-0.5 sm:mb-1 shrink-0 leading-none', isEmpty ? 'opacity-70' : '']"
      aria-hidden="true"
    >{{ axisIcon }}</div>

    <div
      :class="[
        'uppercase tracking-tight leading-[1.1] px-0.5 break-words line-clamp-3 sm:line-clamp-2',
        labelClass,
        isEmpty ? 'text-bingo-textMuted' : '',
      ]"
    >
      {{ cell.label }}
    </div>

    <div
      v-if="state.playerName"
      :class="[
        'mt-0.5 sm:mt-1 font-bold uppercase tracking-tight opacity-90 leading-[1.05] break-words w-full line-clamp-2',
        playerNameClass,
      ]"
    >
      {{ state.playerName }}
    </div>
  </button>
</template>
