<script setup>
import { computed, ref } from 'vue'
import { CELL_STATUS } from '../stores/game.js'

const props = defineProps({
  cell: { type: Object, required: true },
  state: { type: Object, required: true },
  index: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false },
  revealErrors: { type: Boolean, default: false },
})

defineEmits(['click'])

const isEmpty = computed(() => props.state.status === CELL_STATUS.EMPTY)
const isFilled = computed(
  () => props.state.status === 'filled' || props.state.status === 'wrong',
)
const showWrong = computed(() => {
  if (!props.revealErrors) return false
  if (props.state.status === 'wrong') return true
  return isFilled.value && props.state.wasCorrect === false
})

// Effet plateau de dames : alternance de teintes selon (row + col) % 2.
// Index 0 = (0,0) = clair, 1 = (0,1) = sombre, ...
const isCheckerLight = computed(
  () => (Math.floor(props.index / 4) + (props.index % 4)) % 2 === 0,
)

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
  if (showWrong.value) return 'bg-bingo-cellLocked text-white'
  if (isFilled.value) return 'bg-bingo-cell text-bingo-textDark'
  // Empty : alternance checkerboard
  return isCheckerLight.value
    ? 'bg-bingo-cellEmptyLight text-white hover:bg-white/10'
    : 'bg-bingo-cellEmpty text-white hover:bg-white/[0.07]'
})

const statusLabel = computed(() => {
  if (showWrong.value) return '✕'
  if (isFilled.value) return '✓'
  return ''
})

const interactable = computed(() => !props.disabled && isEmpty.value)

const LOGO_FILE_MAP = { phi: 'phl', uta: 'uth' }
const LOGO_EXT_MAP = { mia: 'gif' }

const teamLogoUrl = computed(() => {
  if (props.cell.axis !== 'TEAM') return null
  if (!props.cell.id?.startsWith('team_')) return null
  const abbr = props.cell.id.slice(5).toLowerCase()
  if (abbr.length !== 3) return null
  const file = LOGO_FILE_MAP[abbr] || abbr
  const ext = LOGO_EXT_MAP[abbr] || 'png'
  return `/logos/${file}.${ext}`
})

const FLAG_ALPHA2 = {
  USA: 'us', FRA: 'fr', CAN: 'ca', SRB: 'rs',
  GRC: 'gr', ESP: 'es', SVN: 'si', DEU: 'de',
  CMR: 'cm', DOM: 'do', TUR: 'tr', FIN: 'fi',
  LTU: 'lt', AUS: 'au', MNE: 'me', HRV: 'hr',
  ARG: 'ar', BIH: 'ba', BRA: 'br', GBR: 'gb',
  ITA: 'it', NGA: 'ng', NGR: 'ng', RUS: 'ru', SWE: 'se',
  AUT: 'at', BEL: 'be', POL: 'pl', PRT: 'pt',
  NLD: 'nl', SVK: 'sk', ROU: 'ro', BGR: 'bg',
  HUN: 'hu', UKR: 'ua', LVA: 'lv', EST: 'ee',
  CHE: 'ch', BHS: 'bs', CZE: 'cz', SEN: 'sn',
  SSD: 'ss', SDN: 'sd', ISR: 'il', GEO: 'ge',
  NZL: 'nz', JPN: 'jp', CHN: 'cn', KOR: 'kr',
  MEX: 'mx', PRI: 'pr', JAM: 'jm', COD: 'cd',
  COG: 'cg', AGO: 'ao', EGY: 'eg', MLI: 'ml',
  ZAF: 'za', TUN: 'tn', VEN: 've', COL: 'co',
  CUB: 'cu', LBN: 'lb', IRN: 'ir', MKD: 'mk',
}

const flagUrl = computed(() => {
  if (props.cell.axis !== 'NATIONALITY') return null
  if (!props.cell.id?.startsWith('nat_')) return null
  const code3 = props.cell.id.slice(4).toUpperCase()
  const code2 = FLAG_ALPHA2[code3]
  if (!code2) return null
  return `https://flagcdn.com/w160/${code2}.png`
})

const imgLoaded = ref(true)
function onImgError() { imgLoaded.value = false }

// Polices adaptatives — plus agressif sur les très longs libellés pour
// éviter l'overflow tout en gardant lisible (>=11px partout).
const labelClass = computed(() => {
  const n = (props.cell.label || '').length
  if (n > 26) return 'text-[10px] sm:text-[11px]'
  if (n > 20) return 'text-[11px] sm:text-xs'
  if (n > 14) return 'text-xs sm:text-sm'
  return 'text-sm sm:text-base'
})

const playerNameClass = computed(() => {
  const n = (props.state.playerName || '').length
  if (n > 22) return 'text-[9px] sm:text-[10px]'
  if (n > 18) return 'text-[10px] sm:text-[11px]'
  return 'text-[11px] sm:text-xs'
})
</script>

<template>
  <button
    :disabled="!interactable"
    :class="[
      'relative px-1.5 py-2 sm:px-2 sm:py-3 transition-colors flex flex-col items-center justify-between gap-1 sm:gap-1.5 text-center font-semibold overflow-hidden h-full w-full',
      cellClasses,
      interactable ? 'cursor-pointer active:brightness-110' : 'cursor-default',
    ]"
    @click="$emit('click', cell.id)"
  >
    <span
      v-if="statusLabel"
      class="absolute top-1 right-1.5 text-[10px] sm:text-xs font-bold opacity-80"
    >{{ statusLabel }}</span>

    <!-- Icône / logo / drapeau -->
    <div class="flex-1 flex items-center justify-center w-full min-h-[40px] sm:min-h-[48px]">
      <img
        v-if="teamLogoUrl && imgLoaded"
        :src="teamLogoUrl"
        alt=""
        class="w-10 h-10 sm:w-12 sm:h-12 object-contain"
        :class="isEmpty ? 'opacity-95' : ''"
        @error="onImgError"
      />
      <img
        v-else-if="flagUrl && imgLoaded"
        :src="flagUrl"
        alt=""
        class="w-10 h-7 sm:w-12 sm:h-9 object-cover rounded-full ring-1 ring-white/15"
        :class="isEmpty ? 'opacity-95' : ''"
        @error="onImgError"
      />
      <div
        v-else
        :class="['text-2xl sm:text-3xl leading-none', isEmpty ? 'opacity-80' : '']"
        aria-hidden="true"
      >{{ axisIcon }}</div>
    </div>

    <!-- Libellé + joueur posé -->
    <div class="w-full flex flex-col items-center justify-end gap-0.5">
      <div
        :class="[
          'uppercase tracking-tight leading-[1.1] break-words line-clamp-3 font-bold w-full',
          labelClass,
          isEmpty ? 'text-bingo-textMuted' : '',
        ]"
      >
        {{ cell.label }}
      </div>

      <div
        v-if="state.playerName"
        :class="[
          'font-extrabold uppercase tracking-tight opacity-95 leading-[1.05] break-words w-full line-clamp-2 mt-0.5',
          playerNameClass,
        ]"
      >
        {{ state.playerName }}
      </div>
    </div>
  </button>
</template>
