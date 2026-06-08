import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './assets/main.css'

// Active les Google Fonts dès qu'elles arrivent — équivalent du
// `onload="this.media='all'"` qui était inline dans index.html, déplacé
// ici pour rester compatible CSP script-src 'self' (pas d'inline handler).
const fontsLink = document.getElementById('google-fonts')
if (fontsLink) {
  if (fontsLink.sheet) {
    fontsLink.media = 'all'
  } else {
    fontsLink.addEventListener('load', () => { fontsLink.media = 'all' }, { once: true })
  }
}

// Cloudflare Web Analytics : injection dynamique du beacon SI le token
// est défini au build (VITE_CF_BEACON_TOKEN). Sinon on n'embarque rien
// — pas de tracker chargé en dev / sans config. Le script tag est créé
// programmatiquement plutôt qu'inline pour rester sous script-src 'self'
// + le whitelist explicite de static.cloudflareinsights.com dans la CSP.
const cfToken = import.meta.env.VITE_CF_BEACON_TOKEN
if (cfToken) {
  const s = document.createElement('script')
  s.defer = true
  s.src = 'https://static.cloudflareinsights.com/beacon.min.js'
  s.setAttribute('data-cf-beacon', JSON.stringify({ token: cfToken }))
  document.head.appendChild(s)
}

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
