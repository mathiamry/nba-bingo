<script setup>
import { ref, computed } from 'vue'
import { useMultiplayerStore } from '../stores/multiplayer.js'

defineProps({
  // Pour permettre au parent de pré-remplir le nom (depuis le solo store par ex.)
  initialName: { type: String, default: '' },
})

const emit = defineEmits(['solo', 'navigate'])

const mp = useMultiplayerStore()
const name = ref(mp.playerName || '')
const joinCode = ref('')

const trimmedName = computed(() => name.value.trim())
const trimmedCode = computed(() => joinCode.value.toUpperCase().replace(/[^A-Z0-9-]/g, '').trim())

function persistName() {
  mp.setPlayerName(trimmedName.value)
}

function makeCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' // ambigus retirés
  let s = ''
  for (let i = 0; i < 4; i++) s += chars[Math.floor(Math.random() * chars.length)]
  return `NBA-${s}`
}

function startSolo() {
  if (trimmedName.value) persistName()
  emit('solo')
}

function createRoom() {
  if (!trimmedName.value) return
  persistName()
  const code = makeCode()
  emit('navigate', `/r/${code}`)
}

function joinRoom() {
  if (!trimmedName.value || !trimmedCode.value) return
  persistName()
  emit('navigate', `/r/${trimmedCode.value}`)
}
</script>

<template>
  <main class="w-full max-w-md px-3 mt-6 flex flex-col gap-5">
    <div class="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col gap-3">
      <label class="text-xs uppercase tracking-widest opacity-60">Ton prénom</label>
      <input
        v-model="name"
        @blur="persistName"
        @keydown.enter="persistName"
        type="text"
        maxlength="24"
        placeholder="Ex. Mathia"
        class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2.5 text-lg font-semibold focus:outline-none focus:border-bingo-cell"
      />
      <p class="text-[11px] opacity-50">Visible par tes amis dans la room. Mémorisé localement pour les prochaines parties.</p>
    </div>

    <button
      class="w-full bg-bingo-cell text-bingo-textDark font-extrabold uppercase tracking-widest py-3.5 rounded-xl hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed text-base"
      :disabled="!trimmedName"
      @click="startSolo"
    >
      Jouer en solo
    </button>

    <div class="grid grid-cols-1 gap-3">
      <button
        class="w-full bg-bingo-header text-white font-bold uppercase tracking-wider py-3 rounded-xl hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
        :disabled="!trimmedName"
        @click="createRoom"
      >
        Créer une room
      </button>

      <div class="bg-white/5 border border-white/10 rounded-xl p-3 flex flex-col gap-2">
        <label class="text-xs uppercase tracking-widest opacity-60 px-1">Rejoindre une room</label>
        <div class="flex gap-2">
          <input
            v-model="joinCode"
            type="text"
            placeholder="NBA-XXXX"
            class="flex-1 bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-center font-mono uppercase tracking-widest focus:outline-none focus:border-bingo-cell"
            @keydown.enter="joinRoom"
          />
          <button
            class="bg-bingo-cell text-bingo-textDark font-bold uppercase tracking-wider px-4 rounded-lg hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="!trimmedName || !trimmedCode"
            @click="joinRoom"
          >
            OK
          </button>
        </div>
      </div>
    </div>

    <p class="text-[11px] text-center opacity-50">
      Le mode multijoueur synchronise les joueurs proposés — tout le monde voit le même au même moment, et le récap final classe les scores.
    </p>
  </main>
</template>
