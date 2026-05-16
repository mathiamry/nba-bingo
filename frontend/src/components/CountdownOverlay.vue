<script setup>
/**
 * Countdown overlay façon JumboTron NBA.
 *
 * Le parent contrôle le cycle de vie : monte le composant quand le
 * serveur passe en phase "countdown", démonte quand on entre en "playing".
 *
 * À chaque changement de `secondsLeft`, on incrémente `tickKey` pour
 * forcer Vue à recréer le <span> du chiffre et le <circle> du ring →
 * les animations CSS repartent de zéro proprement.
 */
import { computed, ref, watch } from 'vue'

const props = defineProps({
  secondsLeft: { type: Number, required: true },
})

const tickKey = ref(0)
watch(() => props.secondsLeft, () => { tickKey.value++ })

// Trois paliers d'urgence pour la couleur du chiffre + ring + glow.
// final = 1 ou 0 : tout vire au rouge + pulse global.
// urgent = 2-3 : magenta (bingo-bgGradient) — l'accent "intensité" de la palette.
// calm = 4-10 : vert lime — couleur sereine, "on chauffe".
const tier = computed(() => {
  if (props.secondsLeft <= 1) return 'final'
  if (props.secondsLeft <= 3) return 'urgent'
  return 'calm'
})
</script>

<template>
  <Transition name="overlay-fade" appear>
    <div
      class="fixed inset-0 z-50 flex flex-col items-center justify-center overflow-hidden bg-bingo-bg/95 backdrop-blur-md"
      :class="tier === 'final' ? 'animate-[overlay-pulse_500ms_ease-out_forwards]' : ''"
      role="status"
      aria-live="assertive"
      :aria-label="`La partie commence dans ${secondsLeft} secondes`"
    >
      <!-- Grain "parquet" — texture SVG inline pour ne pas dépendre d'un asset. -->
      <div class="absolute inset-0 opacity-[0.07] mix-blend-overlay pointer-events-none bg-noise"></div>

      <!-- Glow radial centré : suit le tier (lime / magenta / rouge). -->
      <div
        class="absolute inset-0 pointer-events-none transition-colors duration-300"
        :class="[
          tier === 'calm'   && 'bg-glow-lime',
          tier === 'urgent' && 'bg-glow-magenta',
          tier === 'final'  && 'bg-glow-red',
        ]"
      ></div>

      <!-- Header rail : "TIP-OFF IN" — kerning très large pour le rythme broadcast. -->
      <div class="relative font-bebas text-white/70 tracking-[0.5em] text-xs sm:text-sm uppercase mb-8 sm:mb-12 pl-[0.5em]">
        Tip-off dans
      </div>

      <!-- Centre : ring shot-clock + chiffre. Tout est en vmin pour rester compact sur mobile. -->
      <div class="relative flex items-center justify-center">
        <!-- Ring SVG : se vide en 1s par tick (stroke-dashoffset animé). -->
        <svg
          viewBox="0 0 100 100"
          class="absolute w-[78vmin] h-[78vmin] max-w-[520px] max-h-[520px] -rotate-90"
          aria-hidden="true"
        >
          <!-- Track : cercle de fond, opacity faible. -->
          <circle cx="50" cy="50" r="46" fill="none" stroke="currentColor"
                  class="text-white/10" stroke-width="0.8"/>
          <!-- Arc actif : drain de 0→100 sur 1s. -->
          <circle
            :key="'arc-' + tickKey"
            cx="50" cy="50" r="46"
            fill="none"
            stroke-width="1.4"
            stroke-linecap="round"
            pathLength="100"
            stroke-dasharray="100"
            stroke-dashoffset="0"
            class="origin-center countdown-arc"
            :class="[
              tier === 'calm'   && 'text-bingo-cell drop-shadow-lime',
              tier === 'urgent' && 'text-bingo-bgGradient drop-shadow-magenta',
              tier === 'final'  && 'text-red-500 drop-shadow-red',
            ]"
            stroke="currentColor"
          />
          <!-- Tick marks aux 4 cardinaux : touche scoreboard LED. -->
          <g class="text-white/30" stroke="currentColor" stroke-width="0.8">
            <line x1="50" y1="2"  x2="50" y2="6" />
            <line x1="50" y1="94" x2="50" y2="98" />
            <line x1="2"  y1="50" x2="6"  y2="50" />
            <line x1="94" y1="50" x2="98" y2="50" />
          </g>
        </svg>

        <!-- Le chiffre — Bebas Neue, fluide via clamp, stamp à chaque tick. -->
        <div
          :key="'num-' + tickKey"
          class="relative font-bebas leading-none tabular-nums tracking-tight countdown-number"
          :class="[
            tier === 'calm'   && 'text-bingo-cell drop-shadow-lime-text',
            tier === 'urgent' && 'text-bingo-bgGradient drop-shadow-magenta-text',
            tier === 'final'  && 'text-red-500 drop-shadow-red-text',
          ]"
          style="font-size: clamp(180px, 56vmin, 460px)"
        >
          {{ secondsLeft }}
        </div>
      </div>

      <!-- Footer rail : signature légère, équilibre la composition verticale. -->
      <div class="relative mt-8 sm:mt-12 font-bebas text-white/40 tracking-[0.4em] text-[10px] sm:text-xs uppercase">
        NBA Bingo · Multiplayer
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* Animations propres au countdown — pas exposées à Tailwind global parce
   qu'elles sont uniques à ce composant. */

@keyframes countdown-arc-drain {
  from { stroke-dashoffset: 0; }
  to   { stroke-dashoffset: 100; }
}
.countdown-arc {
  animation: countdown-arc-drain 1s linear forwards;
}

/* Stamp du chiffre : entrée énergique, overshoot, settle. Plus appuyé
   que le `cellStamp` du board parce qu'on veut un effet broadcast. */
@keyframes countdown-number-pop {
  0%   { transform: scale(0.55); opacity: 0; filter: blur(10px); }
  40%  { transform: scale(1.18); opacity: 1; filter: blur(0); }
  70%  { transform: scale(0.95); }
  100% { transform: scale(1);    opacity: 1; }
}
.countdown-number {
  animation: countdown-number-pop 380ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

/* Pulse global rouge déclenché au palier "final" (1, 0). Un seul shot,
   redéclenché par re-key implicite via classe conditionnelle. */
@keyframes overlay-pulse {
  0%   { background-color: rgb(30 13 48 / 0.95); }
  40%  { background-color: rgb(127 0 0 / 0.7); }
  100% { background-color: rgb(30 13 48 / 0.95); }
}

/* Fade enter/leave de l'overlay entier (Transition Vue). */
.overlay-fade-enter-active,
.overlay-fade-leave-active {
  transition: opacity 220ms ease-out, transform 220ms ease-out;
}
.overlay-fade-enter-from,
.overlay-fade-leave-to {
  opacity: 0;
  transform: scale(1.04);
}

/* Grain parquet — SVG inline en data URI, pas de fetch réseau. */
.bg-noise {
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.6 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
}

/* Glows radiaux — chaque tier a le sien, transition fluide via la classe
   parente .transition-colors qui anime le background. */
.bg-glow-lime {
  background: radial-gradient(circle at center, rgb(204 232 62 / 0.18) 0%, transparent 55%);
}
.bg-glow-magenta {
  background: radial-gradient(circle at center, rgb(184 55 198 / 0.28) 0%, transparent 55%);
}
.bg-glow-red {
  background: radial-gradient(circle at center, rgb(255 60 60 / 0.35) 0%, transparent 55%);
}

/* Drop shadows colorées : font ressortir le ring et le chiffre comme s'ils
   étaient des LED. drop-shadow plutôt que box-shadow pour suivre la forme. */
.drop-shadow-lime { filter: drop-shadow(0 0 24px rgb(204 232 62 / 0.6)); }
.drop-shadow-magenta { filter: drop-shadow(0 0 28px rgb(184 55 198 / 0.7)); }
.drop-shadow-red { filter: drop-shadow(0 0 32px rgb(255 60 60 / 0.8)); }

.drop-shadow-lime-text {
  text-shadow:
    0 0 18px rgb(204 232 62 / 0.55),
    0 0 56px rgb(204 232 62 / 0.35);
}
.drop-shadow-magenta-text {
  text-shadow:
    0 0 22px rgb(184 55 198 / 0.7),
    0 0 64px rgb(184 55 198 / 0.45);
}
.drop-shadow-red-text {
  text-shadow:
    0 0 24px rgb(255 60 60 / 0.8),
    0 0 70px rgb(255 60 60 / 0.55);
}

/* Accessibilité : si l'utilisateur préfère réduire les animations, on
   garde la fonction (affichage du chiffre) mais on coupe les keyframes. */
@media (prefers-reduced-motion: reduce) {
  .countdown-arc,
  .countdown-number {
    animation: none;
  }
  .overlay-fade-enter-active,
  .overlay-fade-leave-active {
    transition: opacity 120ms linear;
  }
}
</style>
