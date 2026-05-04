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
    return e.sort((a, b) => b.score - a.score || b.correct - a.correct || a.name.localeCompare(b.name))
  }
  return e.sort((a, b) => b.placed - a.placed || a.name.localeCompare(b.name))
})

function fmt(n) {
  return Number(n.toFixed(2))
}
</script>

<template>
  <section class="bg-white/5 border border-white/10 rounded-xl p-3">
    <div class="text-[11px] uppercase tracking-widest opacity-60 mb-2 px-1 flex justify-between">
      <span>Leaderboard</span>
      <span v-if="!reveal" class="opacity-50">cases posées</span>
      <span v-else>score</span>
    </div>
    <ul class="space-y-1">
      <li
        v-for="(e, i) in sorted"
        :key="e.id"
        :class="['flex items-center gap-2 px-2 py-1.5 rounded text-sm', e.id === selfId ? 'bg-bingo-cell/10' : '']"
      >
        <span class="w-5 text-center font-bold opacity-60 tabular-nums">{{ i + 1 }}</span>
        <span class="flex-1 font-semibold truncate">{{ e.name }}<span v-if="e.id === selfId" class="opacity-50 ml-1">(toi)</span></span>
        <span v-if="!reveal" class="tabular-nums opacity-80">{{ e.placed }} / {{ total }}</span>
        <span v-else class="tabular-nums font-bold text-bingo-cell">{{ fmt(e.score) }}</span>
      </li>
    </ul>
  </section>
</template>
