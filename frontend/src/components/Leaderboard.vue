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
    return e.sort((a, b) =>
      // 1. Score : plus haut = mieux
      b.score - a.score ||
      // 2. Moins de cases passées = mieux
      (a.skipped ?? 0) - (b.skipped ?? 0) ||
      // 3. Temps : plus rapide = mieux (0 = pas fini → en dernier)
      ((a.completedAtMs || Infinity) - (b.completedAtMs || Infinity)) ||
      a.name.localeCompare(b.name),
    )
  }
  return e.sort(
    (a, b) => b.placed - a.placed || a.name.localeCompare(b.name),
  )
})

function fmtScore(n) {
  return Number((n ?? 0).toFixed(2))
}

function fmtDuration(ms) {
  if (!ms || ms < 0) return '—'
  const s = Math.round(ms / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m${String(s % 60).padStart(2, '0')}s`
}
</script>

<template>
  <section class="bg-white/5 border border-white/10 rounded-xl p-3">
    <div class="text-[11px] uppercase tracking-widest opacity-60 mb-2 px-1 flex justify-between">
      <span>Leaderboard</span>
      <span v-if="!reveal" class="opacity-50">cases posées</span>
      <span v-else>score · skips · temps</span>
    </div>
    <ul class="space-y-1">
      <li
        v-for="(e, i) in sorted"
        :key="e.id"
        :class="[
          'flex items-center gap-2 px-2 py-1.5 rounded text-sm',
          e.id === selfId ? 'bg-bingo-cell/10' : '',
        ]"
      >
        <span class="w-5 text-center font-bold opacity-60 tabular-nums">{{ i + 1 }}</span>
        <span class="flex-1 font-semibold truncate">
          {{ e.name }}<span v-if="e.id === selfId" class="opacity-50 ml-1">(toi)</span>
        </span>

        <!-- Pendant la partie : juste le compte de placements -->
        <span v-if="!reveal" class="tabular-nums opacity-80">
          {{ e.placed }} / {{ total }}
        </span>

        <!-- À la fin : score (gros) + skips + temps -->
        <template v-else>
          <span class="tabular-nums font-bold text-bingo-cell">{{ fmtScore(e.score) }}</span>
          <span class="tabular-nums text-[10px] opacity-60" :title="`${e.skipped} cases passées`">
            ⤼ {{ e.skipped ?? 0 }}
          </span>
          <span class="tabular-nums text-[10px] opacity-60" :title="`Temps de complétion`">
            ⏱ {{ fmtDuration(e.durationMs) }}
          </span>
        </template>
      </li>
    </ul>
  </section>
</template>
