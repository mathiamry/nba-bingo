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

// Checkerboard: alternation by (row + col) % 2
const isCheckerLight = computed(
  () => (Math.floor(props.index / 4) + (props.index % 4)) % 2 === 0,
)

// ── Specific emoji per cell id, falls back to axis default ───────────────
const AWARD_EMOJI = {
  award_mvp: '👑',
  award_finals_mvp: '🏆',
  award_dpoy: '🛡️',
  award_roy: '🌟',
  award_6moy: '💺',
  award_all_star: '⭐',
  award_all_nba: '✨',
  award_olympic_gold_2024: '🥇',
  award_olympic_silver_fra: '🥈',
}

function emojiFor(id, axis) {
  if (id && AWARD_EMOJI[id]) return AWARD_EMOJI[id]
  // STAT variants
  if (id?.includes('ppg')) return '🎯'
  if (id?.includes('rpg')) return '💪'
  if (id?.includes('apg')) return '🎲'
  // ERA
  if (id === 'era_2020s') return '🆕'
  // COMBO
  if (id?.startsWith('combo_')) return '💎'
  // Axis defaults
  switch (axis) {
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
}

const axisIcon = computed(() => emojiFor(props.cell.id, props.cell.axis))

const cellClasses = computed(() => {
  if (showWrong.value)
    return 'bg-bingo-cellLocked text-white'
  if (isFilled.value)
    return 'bg-bingo-cell text-bingo-textDark'
  // Empty: checkerboard with inner top-highlight shimmer via box-shadow
  return isCheckerLight.value
    ? 'bg-bingo-cellEmptyLight text-white hover:brightness-125 active:brightness-150'
    : 'bg-bingo-cellEmpty text-white hover:brightness-125 active:brightness-150'
})

// Animation class applied only when transitioning to filled/wrong state
const animateIn = computed(() => isFilled.value || showWrong.value)

const statusLabel = computed(() => {
  // On affiche uniquement le ✕ rouge pour les erreurs révélées en fin de
  // partie. Pour les cases correctes, le fond lime suffit comme indicateur.
  if (showWrong.value) return '✕'
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

// Adaptive label font size — on shrink plus tôt pour que les noms de
// pays/équipes 8-9 caractères ("CAMEROUN", "WARRIORS", "LITUANIE",
// "MAVERICKS") tiennent sur UNE seule ligne au sm: breakpoint, où le
// précédent text-base (16px) débordait sur la largeur de cellule.
const labelClass = computed(() => {
  const n = (props.cell.label || '').length
  if (n > 26) return 'text-[10px] sm:text-[11px]'
  if (n > 20) return 'text-[11px] sm:text-xs'
  if (n > 14) return 'text-xs sm:text-sm'
  if (n > 7)  return 'text-xs sm:text-sm'
  return 'text-sm sm:text-base'
})

// Label tracking: short labels breathe more
const labelTracking = computed(() => {
  const n = (props.cell.label || '').length
  if (n <= 8) return 'tracking-widest'
  if (n <= 14) return 'tracking-wide'
  return 'tracking-tight'
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
      revealErrors ? 'rounded-xl' : 'rounded-none',
      cellClasses,
      animateIn ? 'animate-cell-in' : '',
      interactable ? 'cursor-pointer' : 'cursor-default',
      // Inner top-edge highlight on empty cells for glassy feel
      isEmpty ? 'shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]' : '',
    ]"
    @click="$emit('click', cell.id)"
  >
    <span
      v-if="statusLabel"
      class="absolute top-1 right-1.5 text-[10px] sm:text-xs font-bold opacity-80"
    >{{ statusLabel }}</span>

    <!-- Icon / logo / flag -->
    <div class="flex-1 flex items-center justify-center w-full min-h-[40px] sm:min-h-[50px]">
      <img
        v-if="teamLogoUrl && imgLoaded"
        :src="teamLogoUrl"
        alt=""
        class="w-10 h-10 sm:w-13 sm:h-13 object-contain drop-shadow-sm"
        :class="isEmpty ? 'opacity-90' : ''"
        @error="onImgError"
      />
      <img
        v-else-if="flagUrl && imgLoaded"
        :src="flagUrl"
        alt=""
        class="w-10 h-7 sm:w-12 sm:h-9 object-cover rounded-sm ring-1 ring-white/20 shadow-sm"
        :class="isEmpty ? 'opacity-90' : ''"
        @error="onImgError"
      />
      <div
        v-else
        :class="['text-2xl sm:text-[1.75rem] leading-none', isEmpty ? 'opacity-75' : '']"
        aria-hidden="true"
      >{{ axisIcon }}</div>
    </div>

    <!-- Label + placed player name -->
    <div class="w-full flex flex-col items-center justify-end gap-0.5">
      <div
        :class="[
          'uppercase leading-[1.15] break-words line-clamp-3 font-bold w-full',
          labelClass,
          labelTracking,
          isEmpty ? 'text-bingo-textMuted' : '',
        ]"
        :style="isEmpty ? 'text-shadow: 0 1px 3px rgba(0,0,0,0.45)' : ''"
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
