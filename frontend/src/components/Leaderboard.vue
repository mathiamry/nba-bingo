<script setup>
import { computed } from 'vue'

const props = defineProps({
  entries: { type: Array, default: () => [] },
  selfId: { type: String, default: '' },
  reveal: { type: Boolean, default: false },
  total: { type: Number, default: 16 },
})

const sorted = computed(() => {
  const e = [...props.entries]
  if (props.reveal) {
    // Tri reveal : joueurs DONE devant (par vrai score), joueurs en cours
    // derrière (le serveur leur renvoie score=0 tant qu'ils ne sont pas
    // finis, on évite donc de les classer "0" parmi les vrais scores).
    return e.sort((a, b) => {
      if (a.done !== b.done) return a.done ? -1 : 1
      // 1. Score : plus haut = mieux
      return (
        b.score - a.score ||
        // 2. Moins de cases passées = mieux
        (a.skipped ?? 0) - (b.skipped ?? 0) ||
        // 3. Temps : plus rapide = mieux (0 = pas fini → en dernier)
        ((a.completedAtMs || Infinity) - (b.completedAtMs || Infinity)) ||
        a.name.localeCompare(b.name)
      )
    })
  }
  // Pendant la partie : displayScore = score réel si done, sinon
  // provisoire. (Conservé pour réutilisation future, ce composant n'est
  // plus monté pendant la phase 'playing' en mode multi.)
  return e.sort((a, b) => {
    const sa = a.done ? (a.score ?? 0) : (a.provisionalScore ?? 0)
    const sb = b.done ? (b.score ?? 0) : (b.provisionalScore ?? 0)
    if (sb !== sa) return sb - sa
    if (a.done !== b.done) return a.done ? -1 : 1
    return (
      b.placed - a.placed ||
      (a.skipped ?? 0) - (b.skipped ?? 0) ||
      a.name.localeCompare(b.name)
    )
  })
})

function fmtScore(n) {
  return Number((n ?? 0).toFixed(0))
}

// Format MM:SS façon Football Bingo (toujours 2 chiffres pour les
// minutes, pad avec zéros). Renvoie '—' si pas de durée connue.
function fmtMMSS(ms) {
  if (!ms || ms < 0) return '—'
  const s = Math.round(ms / 1000)
  const mm = String(Math.floor(s / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${mm}:${ss}`
}
</script>

<template>
  <!--
    Leaderboard recap (style Football Bingo) : ligne d'en-tête avec dot
    LIVE + colonnes Time / Pld / Pts. Une ligne par joueur, ligne lime
    pleine pour "you" + pill noire YOU. Les ex-aequo se distinguent par
    le tie-breaker (skips puis temps).
  -->
  <section class="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
    <!-- Header -->
    <div class="flex items-center px-4 py-3 text-[11px] sm:text-xs uppercase tracking-wider opacity-70">
      <span class="flex items-center gap-1.5 flex-1 min-w-0">
        <span
          class="w-2 h-2 rounded-full"
          :class="reveal ? 'bg-white/40' : 'bg-bingo-cell animate-pulse'"
        ></span>
        <span class="font-semibold tracking-widest">{{ reveal ? 'Final' : 'Live' }}</span>
      </span>
      <span class="w-14 sm:w-16 text-right">Time</span>
      <span class="w-10 sm:w-12 text-right">Pld</span>
      <span class="w-12 sm:w-14 text-right">Pts</span>
    </div>

    <ul class="divide-y divide-white/10">
      <li
        v-for="(e, i) in sorted"
        :key="e.id"
        :class="[
          'flex items-center px-4 py-3 transition-colors',
          e.id === selfId
            ? 'bg-bingo-cell text-bingo-textDark font-bold'
            : '',
          e.connected === false ? 'opacity-60' : '',
        ]"
      >
        <!-- Rank + name + YOU pill -->
        <span class="flex items-center gap-3 flex-1 min-w-0">
          <span
            class="font-bebas text-xl sm:text-2xl tabular-nums w-5 text-center"
            :class="e.id === selfId ? '' : 'opacity-70'"
          >{{ i + 1 }}</span>
          <span class="flex items-center gap-2 min-w-0">
            <span class="font-semibold truncate text-sm sm:text-base">{{ e.name }}</span>
            <span
              v-if="e.id === selfId"
              class="text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full bg-black text-white font-bold flex-shrink-0"
            >You</span>
            <span
              v-if="e.connected === false"
              class="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-yellow-400/15 text-yellow-700"
              :class="e.id === selfId ? '' : 'text-yellow-300/90'"
              title="Déconnecté"
            >Off</span>
          </span>
        </span>

        <!--
          Joueur DONE : Time / Pld / Pts réels affichés.
          Joueur EN COURS : compteur de cases live + tag "En cours" en
          remplacement du score (qui n'est pas encore révélé).
        -->
        <template v-if="e.done">
          <span class="w-14 sm:w-16 text-right tabular-nums font-bebas text-lg sm:text-xl tracking-wide">
            {{ fmtMMSS(e.durationMs) }}
          </span>
          <span class="w-10 sm:w-12 text-right tabular-nums font-bebas text-lg sm:text-xl tracking-wide">
            {{ e.placed ?? 0 }}
          </span>
          <span
            class="w-12 sm:w-14 text-right tabular-nums font-bebas text-2xl sm:text-3xl tracking-wide"
            :class="e.id === selfId ? '' : 'text-white'"
          >{{ fmtScore(e.score) }}</span>
        </template>
        <template v-else>
          <span class="flex-shrink-0 text-[10px] uppercase tracking-widest opacity-70 mr-2">
            En cours
          </span>
          <span class="w-10 sm:w-12 text-right tabular-nums font-bebas text-lg sm:text-xl tracking-wide opacity-80">
            {{ e.placed ?? 0 }}
          </span>
          <span class="w-12 sm:w-14 text-right font-bebas text-2xl sm:text-3xl tracking-wide opacity-50">—</span>
        </template>
      </li>
    </ul>
  </section>
</template>
