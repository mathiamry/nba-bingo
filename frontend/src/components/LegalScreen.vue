<script setup>
import { computed } from 'vue'
import { t } from '../i18n.js'

defineEmits(['back'])

const AUTHOR = 'Elhadji Mamadou Thiam'
const REPO_URL = 'https://github.com/mathiamry/nba-bingo'
const PARTYKIT_URL = 'https://www.partykit.io'
const NBA_API_URL = 'https://github.com/swar/nba_api'
const CLEAR_CMD = 'localStorage.clear()'

// Découpage des paragraphes localisés sur un mot-clé connu, pour insérer
// un <a> ou un <code> au milieu sans `v-html` (incompatible avec la CSP).
// `splitAround(text, kw)` renvoie [avant, après]. Si le mot-clé est absent
// (string mal localisée), on retombe sur [text, ''] qui reste affichable.
function splitAround(text, kw) {
  const idx = text.indexOf(kw)
  if (idx === -1) return [text, '']
  return [text.slice(0, idx), text.slice(idx + kw.length)]
}

const mentionsP1Parts = computed(() => splitAround(t('legal.mentionsP1', { name: AUTHOR }), 'PartyKit'))
const mentionsP2Parts = computed(() => splitAround(t('legal.mentionsP2'), 'GitHub'))
const creditsBodyParts = computed(() => splitAround(t('legal.creditsBody'), 'nba_api'))
</script>

<template>
  <main class="w-full max-w-2xl px-4 mt-6 mb-10 flex flex-col gap-6 text-sm leading-relaxed">
    <button
      type="button"
      class="self-start text-xs uppercase tracking-widest opacity-70 hover:opacity-100"
      @click="$emit('back')"
    >
      {{ t('legal.back') }}
    </button>

    <section class="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col gap-3">
      <h2 class="text-xl font-semibold">{{ t('legal.mentionsTitle') }}</h2>
      <p>
        {{ mentionsP1Parts[0] }}<a
          :href="PARTYKIT_URL"
          target="_blank"
          rel="noopener noreferrer"
          class="underline"
        >PartyKit</a>{{ mentionsP1Parts[1] }}
      </p>
      <p>
        {{ mentionsP2Parts[0] }}<a
          :href="REPO_URL"
          target="_blank"
          rel="noopener noreferrer"
          class="underline"
        >GitHub</a>{{ mentionsP2Parts[1] }}
      </p>
      <p>{{ t('legal.mentionsP3') }}</p>
    </section>

    <section class="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col gap-3">
      <h2 class="text-xl font-semibold">{{ t('legal.privacyTitle') }}</h2>
      <p class="opacity-90">{{ t('legal.privacyIntro') }}</p>

      <div class="bg-black/30 rounded-xl p-4 flex flex-col gap-2">
        <p><strong>{{ t('legal.privacyLocalTitle') }}</strong></p>
        <ul class="list-disc list-inside space-y-1 opacity-90">
          <li>{{ t('legal.privacyLocal1') }}</li>
          <li>{{ t('legal.privacyLocal2') }}</li>
        </ul>
        <p class="text-xs opacity-70 mt-1">
          {{ t('legal.privacyLocalHintBefore') }}<code class="bg-black/40 px-1 rounded">{{ CLEAR_CMD }}</code>{{ t('legal.privacyLocalHintAfter') }}
        </p>
      </div>

      <div class="bg-black/30 rounded-xl p-4 flex flex-col gap-2">
        <p><strong>{{ t('legal.privacyServerTitle') }}</strong></p>
        <ul class="list-disc list-inside space-y-1 opacity-90">
          <li>{{ t('legal.privacyServer1') }}</li>
          <li>{{ t('legal.privacyServer2') }}</li>
        </ul>
        <p class="text-xs opacity-70 mt-1">{{ t('legal.privacyServerHint') }}</p>
      </div>

      <p class="text-xs opacity-70">{{ t('legal.privacyFooter') }}</p>
    </section>

    <section class="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col gap-3">
      <h2 class="text-xl font-semibold">{{ t('legal.creditsTitle') }}</h2>
      <p class="opacity-90">
        {{ creditsBodyParts[0] }}<a
          :href="NBA_API_URL"
          target="_blank"
          rel="noopener noreferrer"
          class="underline"
        >nba_api</a>{{ creditsBodyParts[1] }}
      </p>
    </section>
  </main>
</template>
