<script setup>
import { computed } from 'vue'

const props = defineProps({
  ended: { type: Boolean, required: true },
  won: { type: Boolean, required: true },
  placedCount: { type: Number, required: true },
  total: { type: Number, required: true },
})

defineEmits(['restart'])

const message = computed(() => {
  if (props.won) return 'BRAVO !'
  if (props.ended) return 'TERMINÉ'
  return `${props.placedCount} / ${props.total}`
})

const tone = computed(() => {
  if (props.won) return 'bg-bingo-cell text-bingo-textDark'
  if (props.ended) return 'bg-white/10 text-white'
  return 'bg-bingo-header text-white'
})
</script>

<template>
  <div :class="['rounded-xl px-4 py-3 flex items-center justify-between gap-3 transition-colors', tone]">
    <span class="text-2xl font-extrabold tracking-wide truncate">{{ message }}</span>

    <button
      v-if="ended"
      class="text-xs px-3 py-1.5 rounded-md bg-black/20 hover:bg-black/40 uppercase tracking-wider font-semibold"
      @click="$emit('restart')"
    >
      Rejouer
    </button>
  </div>
</template>
