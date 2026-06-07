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

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
