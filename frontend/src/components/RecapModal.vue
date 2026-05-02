<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  playerName: { type: String, default: '' },
  score: { type: Number, default: 0 },
  placed: { type: Number, default: 0 },
  total: { type: Number, default: 16 },
  errorsCount: { type: Number, default: 0 },
  won: { type: Boolean, default: false },
})

const emit = defineEmits(['name', 'restart', 'close'])

const inputName = ref(props.playerName)
const editing = ref(!props.playerName)
const inputRef = ref(null)

watch(
  () => [props.show, props.playerName],
  async ([show, name]) => {
    if (show && !name) {
      editing.value = true
      inputName.value = ''
      await nextTick()
      inputRef.value?.focus()
    } else if (show && name) {
      editing.value = false
    }
  },
  { immediate: true },
)

function submitName() {
  const value = inputName.value.trim()
  if (!value) return
  emit('name', value)
  editing.value = false
}

function startEdit() {
  inputName.value = props.playerName
  editing.value = true
  nextTick(() => inputRef.value?.focus())
}

const fmtScore = computed(() => Number(props.score.toFixed(2)))
</script>

<template>
  <Transition name="fade">
    <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="$emit('close')"></div>

      <div class="relative bg-bingo-bg border-2 border-bingo-cell rounded-2xl p-7 w-full max-w-sm shadow-2xl text-center">
        <button
          class="absolute top-3 right-3 w-8 h-8 rounded-full hover:bg-white/10 text-lg leading-none"
          aria-label="Fermer"
          @click="$emit('close')"
        >
          ×
        </button>

        <!-- Saisie du nom -->
        <template v-if="editing">
          <h2 class="text-xl font-extrabold mb-1 uppercase tracking-wider">
            Comment tu t'appelles ?
          </h2>
          <p class="text-xs opacity-60 mb-5">On garde ton nom pour les prochaines parties.</p>
          <input
            ref="inputRef"
            v-model="inputName"
            class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-center text-lg font-semibold focus:outline-none focus:border-bingo-cell"
            placeholder="Ton prénom"
            maxlength="24"
            @keydown.enter="submitName"
          />
          <button
            :disabled="!inputName.trim()"
            class="mt-4 w-full bg-bingo-cell text-bingo-textDark font-bold uppercase tracking-wider py-2.5 rounded-lg hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
            @click="submitName"
          >
            Voir mon score
          </button>
        </template>

        <!-- Score -->
        <template v-else>
          <div class="text-xs uppercase tracking-widest opacity-60 mb-1">
            {{ won ? 'Champion' : 'Joueur' }}
          </div>
          <div class="text-2xl font-extrabold mb-5 flex items-center justify-center gap-2">
            <span class="truncate max-w-[200px]">{{ playerName }}</span>
            <button
              class="text-xs opacity-50 hover:opacity-100 underline"
              title="Modifier le nom"
              @click="startEdit"
            >
              modifier
            </button>
          </div>

          <div class="text-xs uppercase tracking-widest opacity-60 mb-1">Score</div>
          <div class="text-7xl font-extrabold text-bingo-cell tabular-nums leading-none mb-1">
            {{ fmtScore }}
          </div>
          <div class="text-xs opacity-60 mb-6">
            {{ placed }}/{{ total }} cases · {{ errorsCount }} erreur{{ errorsCount > 1 ? 's' : '' }}
          </div>

          <div class="flex flex-col gap-2">
            <button
              class="w-full bg-bingo-cell text-bingo-textDark font-bold uppercase tracking-wider py-2.5 rounded-lg hover:brightness-110"
              @click="$emit('restart')"
            >
              Rejouer
            </button>
            <button
              class="w-full bg-white/10 text-white font-semibold uppercase tracking-wider py-2 rounded-lg hover:bg-white/20 text-xs"
              @click="$emit('close')"
            >
              Voir la grille
            </button>
          </div>
        </template>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
