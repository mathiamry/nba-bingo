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
  return null
})

const tone = computed(() => {
  if (props.won) return 'bg-bingo-cell text-bingo-textDark'
  if (props.ended) return 'bg-white/10 text-white'
  return 'bg-bingo-header text-white'
})
</script>

<template>
  <div
    :class="[
      'rounded-2xl px-4 py-3 sm:px-5 sm:py-4 flex items-center justify-between gap-3 transition-colors',
      tone,
    ]"
  >
    <div class="flex flex-col">
      <span
        v-if="message"
        class="text-3xl sm:text-4xl font-bebas tracking-widest leading-none"
      >{{ message }}</span>
      <span
        v-else
        class="text-3xl sm:text-4xl font-bebas tabular-nums tracking-wide leading-none"
      >{{ placedCount }} <span class="opacity-60">/ {{ total }}</span></span>
      <span
        v-if="!ended"
        class="text-[10px] sm:text-xs uppercase tracking-[0.2em] opacity-70 mt-1"
      >cases posées</span>
    </div>

    <button
      v-if="ended"
      class="text-base sm:text-lg px-3 py-2 sm:px-4 sm:py-2.5 rounded-lg bg-black/25 hover:bg-black/40 uppercase tracking-widest font-bebas"
      @click="$emit('restart')"
    >
      Rejouer
    </button>
  </div>
</template>
