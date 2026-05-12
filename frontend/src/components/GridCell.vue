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

// Damier (checkerboard) : alternance par (row + col) % 2. Donne le look
// "plateau de dames" du Football Bingo avec deux tons de purple subtils.
const isCheckerLight = computed(
  () => (Math.floor(props.index / 4) + (props.index % 4)) % 2 === 0,
)

// Texte / couleur de l'état "rempli". Le rendu visuel passe par une
// tuile inset rounded (cf. template). Empty cells utilisent un damier
// 2 tons.
const cellClasses = computed(() => {
  if (showWrong.value || isFilled.value)
    return 'text-bingo-textDark'
  // Empty : damier subtil entre deux tons purple. `hover:` filtré par
  // hoverOnlyWhenSupported (cf. tailwind.config.js) → ne se déclenche
  // pas sur tap mobile.
  return isCheckerLight.value
    ? 'bg-bingo-cellEmptyLight text-white hover:brightness-125 active:brightness-150'
    : 'bg-bingo-cellEmpty text-white hover:brightness-125 active:brightness-150'
})

// Couleur de la tuile inset (filled) — on garde la nuance lime pour les
// placements en cours, et bascule au rouge cellLocked une fois la mauvaise
// réponse révélée.
const tileBgClass = computed(() =>
  showWrong.value ? 'bg-bingo-cellLocked' : 'bg-bingo-cell',
)

const showTile = computed(() => isFilled.value || showWrong.value)

const statusLabel = computed(() => {
  // On affiche uniquement le ✕ rouge pour les erreurs révélées en fin de
  // partie. Pour les cases correctes, le fond lime suffit comme indicateur.
  if (showWrong.value) return '✕'
  return ''
})

const interactable = computed(() => !props.disabled && isEmpty.value)

// Logos SVG officiels NBA téléchargés depuis cdn.nba.com et stockés en
// local sous `frontend/public/logos/{abbr}.svg`. Fini les PNG/GIF qui
// avaient parfois un fond blanc — les SVG vectoriels rendent sans halo et
// restent crisp à toutes les tailles. Plus de LOGO_FILE_MAP / LOGO_EXT_MAP
// nécessaires : tous les fichiers suivent maintenant `{abbr}.svg`.
const teamLogoUrl = computed(() => {
  if (props.cell.axis !== 'TEAM') return null
  if (!props.cell.id?.startsWith('team_')) return null
  const abbr = props.cell.id.slice(5).toLowerCase()
  if (abbr.length !== 3) return null
  return `/logos/${abbr}.svg`
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
  // SVG vector au lieu de PNG raster :
  // - aucun halo blanc / bordure d'antialiasing au crop circulaire
  // - crisp peu importe la résolution (retina 3x sur petites cellules
  //   mobile, ou écran 4K)
  // - taille plus petite en moyenne (~5-15 KB vs ~30-60 KB en PNG w320)
  return `https://flagcdn.com/${code2}.svg`
})

const imgLoaded = ref(true)
function onImgError() { imgLoaded.value = false }

// Adaptive label font size — Bebas Neue est condensé donc on peut se
// permettre un cran de plus que Montserrat à largeur égale. Bumpé d'une
// échelle pour matcher la lisibilité Football Bingo (cf. "PREMIER LEAGUE
// GOLDEN BOOT" qui tient sur 3 lignes en text-lg sur leur grille mobile).
const labelClass = computed(() => {
  const n = (props.cell.label || '').length
  if (n > 26) return 'text-xs sm:text-sm'
  if (n > 20) return 'text-sm sm:text-base'
  if (n > 14) return 'text-sm sm:text-base'
  if (n > 7)  return 'text-base sm:text-lg'
  return 'text-lg sm:text-2xl'
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
  if (n > 22) return 'text-[10px] sm:text-[11px]'
  if (n > 18) return 'text-[11px] sm:text-xs'
  return 'text-xs sm:text-sm'
})
</script>

<template>
  <!--
    Cellule edge-to-edge épurée (style FB) : pas de glow inset, pas de
    radius. Quand elle est REMPLIE : tuile inset rounded-md superposée
    en absolute, avec animation de "stamp" (scale overshoot).
    `touch-manipulation` désactive le délai 300ms iOS et le double-tap
    zoom qui faisaient parfois "rater" un premier tap.
  -->
  <button
    :disabled="!interactable"
    :class="[
      'relative touch-manipulation px-1.5 py-2 sm:px-2 sm:py-3 transition-colors flex flex-col items-center justify-between gap-1 sm:gap-1.5 text-center font-semibold overflow-hidden h-full w-full rounded-none',
      cellClasses,
      interactable ? 'cursor-pointer' : 'cursor-default',
    ]"
    @click="$emit('click', cell.id)"
  >
    <!--
      Tuile colorée inset (le "stamp" à la pose) : flat, juste la couleur
      + le radius. Plus de ring ni de shadow — style FB pur.
      <Transition> garantit que l'animation joue UNE SEULE FOIS, au moment
      où showTile passe de false → true (mount du noeud). Les broadcasts WS
      ultérieurs patchent le parent mais ne remontent pas ce noeud, donc
      l'animation ne se re-déclenche jamais. will-change + translateZ(0)
      forcent un layer GPU composite pour éviter le CPU-paint sur mobile.
    -->
    <Transition name="cell-stamp">
      <span
        v-if="showTile"
        aria-hidden="true"
        :class="[
          'absolute inset-0.5 sm:inset-1 rounded-md pointer-events-none',
          tileBgClass,
        ]"
        style="will-change: transform, opacity; transform: translateZ(0);"
      ></span>
    </Transition>
    <span
      v-if="statusLabel"
      class="absolute top-1 right-1.5 text-[10px] sm:text-xs font-bold opacity-80 z-20"
    >{{ statusLabel }}</span>

    <!--
      Icon / logo / flag : taille remontée pour matcher la prééminence
      visuelle des logos Football Bingo (~50-60% de la hauteur de cellule).
      Les drapeaux pays passent en cercle (object-cover crop centré) car FB
      utilise des flag avatars circulaires plutôt que les rectangles 4:3.
      `sm:w-13` (non-standard Tailwind) corrigé en `sm:w-16`.
      `relative z-10` pour que le contenu reste au-dessus de la tuile inset
      (qui est `absolute` donc empile au-dessus des enfants statiques sinon).
    -->
    <!--
      Logos / drapeaux / emojis épurés : sans drop-shadow ni ring épais.
      Le drapeau pays garde un ring fin pour se détacher des cases vides
      sombres, mais nettement plus discret qu'avant.
    -->
    <div class="relative z-10 flex-1 flex items-center justify-center w-full min-h-[56px] sm:min-h-[72px]">
      <img
        v-if="teamLogoUrl && imgLoaded"
        :src="teamLogoUrl"
        alt=""
        class="w-14 h-14 sm:w-20 sm:h-20 object-contain"
        @error="onImgError"
      />
      <img
        v-else-if="flagUrl && imgLoaded"
        :src="flagUrl"
        alt=""
        class="w-12 h-12 sm:w-16 sm:h-16 object-cover rounded-full ring-1 ring-white/15"
        @error="onImgError"
      />
      <div
        v-else
        class="text-3xl sm:text-5xl leading-none"
        aria-hidden="true"
      >{{ axisIcon }}</div>
    </div>

    <!-- Label + placed player name (relative z-10 cf. icon ci-dessus) -->
    <div class="relative z-10 w-full flex flex-col items-center justify-end gap-0.5">
      <!--
        Label : blanc franc sur les cases vides (au lieu du textMuted lavande
        qui rendait les labels "abstraits" / peu lisibles côté FB). Sur les
        cases lime (filled), `cellClasses` impose déjà text-bingo-textDark.
      -->
      <!--
        Label : blanc franc sans text-shadow (style FB épuré). Le contraste
        blanc / cellEmpty purple #2c1f3f (ratio ~9:1) est largement
        suffisant pour la lisibilité.
      -->
      <div
        :class="[
          'font-bebas uppercase leading-[1.1] break-words line-clamp-3 w-full',
          labelClass,
          labelTracking,
          isEmpty ? 'text-white' : '',
        ]"
      >
        {{ cell.label }}
      </div>

      <div
        v-if="state.playerName"
        :class="[
          'font-bebas uppercase tracking-wide opacity-95 leading-[1.05] break-words w-full line-clamp-2 mt-0.5',
          playerNameClass,
        ]"
      >
        {{ state.playerName }}
      </div>
    </div>
  </button>
</template>

<style scoped>
/*
  Classes injectées par <Transition name="cell-stamp"> au mount du tile.
  Vue applique :
    - .cell-stamp-enter-from  (frame 0 — noeud vient d'être inséré)
    - .cell-stamp-enter-active (toute la durée de la transition)
    - .cell-stamp-enter-to    (état final, tenu via forwards)
  Après la fin de l'animation Vue retire -enter-from et -enter-active.
  Le noeud reste dans le DOM avec son état final — aucune réapplication
  des classes d'animation ne peut se produire lors des re-renders suivants.
*/
.cell-stamp-enter-active {
  animation: cellStamp 280ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.cell-stamp-enter-from {
  opacity: 0;
  transform: translateZ(0) scale(0.6);
}

.cell-stamp-enter-to {
  opacity: 1;
  transform: translateZ(0) scale(1);
}

@keyframes cellStamp {
  0%   { opacity: 0; transform: translateZ(0) scale(0.6); }
  55%  { opacity: 1; transform: translateZ(0) scale(1.08); }
  80%  { opacity: 1; transform: translateZ(0) scale(0.97); }
  100% { opacity: 1; transform: translateZ(0) scale(1); }
}
</style>
