<script setup>
import { ref, computed } from 'vue'
import { useMultiplayerStore } from '../stores/multiplayer.js'
import { t, locale, setLocale } from '../i18n.js'

function toggleLocale() {
  setLocale(locale.value === 'fr' ? 'en' : 'fr')
}

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
  // 5 caractères dans un alphabet de 31 → ~28M combos. À 4 chars on tombait
  // à ~924k, énumérable par un bot en quelques minutes. Tirage via
  // crypto.getRandomValues quand dispo, sinon fallback Math.random.
  const len = 5
  let bytes
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    bytes = new Uint32Array(len)
    crypto.getRandomValues(bytes)
  }
  let s = ''
  for (let i = 0; i < len; i++) {
    const r = bytes ? bytes[i] : Math.floor(Math.random() * 0xffffffff)
    s += chars[r % chars.length]
  }
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
      <label class="text-xs uppercase tracking-widest opacity-60">{{ t('home.firstNameLabel') }}</label>
      <input
        v-model="name"
        @blur="persistName"
        @keydown.enter="persistName"
        type="text"
        maxlength="24"
        :placeholder="t('home.firstNamePlaceholder')"
        class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2.5 text-lg font-semibold focus:outline-none focus:border-bingo-cell"
      />
      <p class="text-[11px] opacity-50">{{ t('home.firstNameHelp') }}</p>
    </div>

    <button
      class="w-full bg-bingo-cell text-bingo-textDark font-bebas uppercase tracking-widest py-3.5 rounded-xl hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed text-xl"
      :disabled="!trimmedName"
      @click="startSolo"
    >
      {{ t('home.solo') }}
    </button>

    <div class="grid grid-cols-1 gap-3">
      <button
        class="w-full bg-bingo-header text-white font-bebas uppercase tracking-widest py-3 rounded-xl hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed text-lg"
        :disabled="!trimmedName"
        @click="createRoom"
      >
        {{ t('home.createRoom') }}
      </button>

      <div class="bg-white/5 border border-white/10 rounded-xl p-3 flex flex-col gap-2">
        <label class="text-xs uppercase tracking-widest opacity-60 px-1">{{ t('home.joinRoomLabel') }}</label>
        <div class="flex gap-2">
          <input
            v-model="joinCode"
            type="text"
            :placeholder="t('home.joinPlaceholder')"
            class="flex-1 bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-center font-mono uppercase tracking-widest focus:outline-none focus:border-bingo-cell"
            @keydown.enter="joinRoom"
          />
          <button
            class="bg-bingo-cell text-bingo-textDark font-bebas uppercase tracking-widest px-4 rounded-lg hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed text-lg"
            :disabled="!trimmedName || !trimmedCode"
            @click="joinRoom"
          >
            {{ t('home.joinOk') }}
          </button>
        </div>
      </div>
    </div>

    <p class="text-[11px] text-center opacity-50">
      {{ t('home.tagline') }}
    </p>

    <footer class="text-[11px] text-center opacity-50 mt-2 pb-3 flex items-center justify-center gap-3">
      <a
        href="#/legal"
        class="hover:opacity-100 underline-offset-2 hover:underline"
        @click.prevent="emit('navigate', '/legal')"
      >{{ t('home.legal') }}</a>
      <span class="opacity-30">·</span>
      <button
        type="button"
        class="hover:opacity-100 underline-offset-2 hover:underline uppercase tracking-wider font-semibold"
        :title="t('common.langLabel')"
        @click="toggleLocale"
      >{{ t('common.switchLang') }}</button>
    </footer>
  </main>
</template>
