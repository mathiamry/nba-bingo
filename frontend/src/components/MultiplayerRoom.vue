<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useMultiplayerStore, ConnStatus } from '../stores/multiplayer.js'
import GridCell from './GridCell.vue'
import PlayerCard from './PlayerCard.vue'
import StatusBanner from './StatusBanner.vue'
import Leaderboard from './Leaderboard.vue'
import CountdownOverlay from './CountdownOverlay.vue'

const props = defineProps({
  roomCode: { type: String, required: true },
})
const emit = defineEmits(['leave'])

const mp = useMultiplayerStore()
const {
  connStatus,
  error,
  serverPhase,
  isHost,
  selfId,
  players,
  leaderboard,
  cells,
  cellStates,
  currentPlayer,
  turnIndex,
  sequenceLength,
  isDone,
  doneCount,
  totalPlayers,
  rules,
  countdownSecondsLeft,
  timerProgress,
  myScore,
  myProvisionalScore,
  myDisplayScore,
  myRank,
  won,
  playerName,
  roomState,
  pendingAction,
} = storeToRefs(mp)

const timeLeftSeconds = computed(() => Math.max(0, mp.timeLeftMs / 1000))

const inputName = ref(playerName.value || '')
const showCopied = ref(false)
// Modal classement : visible quand l'utilisateur clique sur "Voir mon
// classement". Disponible dès qu'il a fini sa propre grille (peu importe
// les autres) — pas besoin d'attendre la phase ENDED globale.
const showRanking = ref(false)

onMounted(() => {
  if (mp.playerName) {
    mp.connect(props.roomCode)
  }
})

onBeforeUnmount(() => {
  mp.disconnect()
})

function submitName() {
  const v = inputName.value.trim()
  if (!v) return
  mp.setPlayerName(v)
  if (!mp.isConnected) {
    mp.connect(props.roomCode)
  }
}

function leave() {
  mp.disconnect()
  emit('leave')
}

async function copyLink() {
  const url = `${window.location.origin}${window.location.pathname}#/r/${props.roomCode}`
  try {
    await navigator.clipboard.writeText(url)
    showCopied.value = true
    setTimeout(() => (showCopied.value = false), 1500)
  } catch {
    // pas grave, le user verra le code à recopier à la main
  }
}

const reveal = computed(() => serverPhase.value === 'ended')

const placedCount = computed(() => {
  const me = leaderboard.value.find((p) => p.id === selfId.value)
  return me?.placed ?? 0
})

const cellGridDisabled = computed(
  () =>
    serverPhase.value !== 'playing' ||
    isDone.value ||
    pendingAction.value ||
    !currentPlayer.value,
)

// Erreur "dure" qui mérite le bandeau rouge bloquant :
// - vraie erreur réseau
// - close prolongé sans aucun state reçu (la connexion n'a jamais abouti)
const fatalError = computed(() => {
  if (connStatus.value === ConnStatus.ERROR) return true
  if (connStatus.value === ConnStatus.CLOSED && !roomState.value) return true
  return false
})

// Petit badge "reconnexion…" pour les coupures transitoires (partysocket
// reconnecte automatiquement, on garde le dernier state pour ne pas
// flasher la UI).
const reconnecting = computed(
  () => connStatus.value === ConnStatus.CLOSED && !!roomState.value,
)
</script>

<template>
  <!--
    Countdown pre-game — overlay plein écran z-50 qui se monte au passage
    en phase "countdown" et se démonte dès qu'on tombe à 0 ou qu'on entre
    en "playing". Le serveur drive le temps absolu, donc tous les clients
    voient le même chiffre au même instant (cf. countdownSecondsLeft dans
    le store, basé sur countdownEndsAt - serverTime).
  -->
  <CountdownOverlay
    v-if="serverPhase === 'countdown' && countdownSecondsLeft > 0"
    :seconds-left="countdownSecondsLeft"
  />

  <main class="w-full max-w-lg px-3 mt-3 flex flex-col gap-3">
    <!--
      Bandeau room : affiché UNIQUEMENT en lobby (pour partager le code/lien
      d'invitation). Une fois la partie lancée ou terminée, ce bandeau
      n'apporte plus rien et prend de la place utile sur mobile — on le
      cache. La flèche retour reste accessible via un bouton compact.
    -->
    <div
      v-if="serverPhase === 'lobby'"
      class="bg-bingo-banner/40 border border-white/10 rounded-xl px-3 py-2 flex items-center gap-2"
    >
      <button
        class="text-white/60 hover:text-white text-lg leading-none px-1"
        title="Quitter la room"
        @click="leave"
      >←</button>
      <div class="flex-1 min-w-0">
        <div class="text-[10px] uppercase tracking-widest opacity-60">Code de la room</div>
        <div class="font-mono font-bold tracking-widest text-base truncate">{{ roomCode }}</div>
      </div>
      <button
        class="text-xs px-3 py-1.5 rounded-md bg-white/10 hover:bg-white/20 uppercase tracking-wider font-semibold"
        @click="copyLink"
      >
        {{ showCopied ? 'Copie ✓' : 'Lien' }}
      </button>
    </div>

    <!-- Bouton retour discret pendant la partie / le recap -->
    <button
      v-else
      class="self-start text-white/50 hover:text-white text-sm px-2 py-1 -ml-2"
      title="Quitter la room"
      @click="leave"
    >← Quitter</button>

    <!-- Saisie du nom si vide -->
    <div v-if="!playerName" class="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col gap-2">
      <label class="text-xs uppercase tracking-widest opacity-60">Ton prénom</label>
      <div class="flex gap-2">
        <input
          v-model="inputName"
          type="text"
          maxlength="24"
          placeholder="Ex. Mathia"
          class="flex-1 bg-white/10 border border-white/20 rounded-lg px-3 py-2 focus:outline-none focus:border-bingo-cell"
          @keydown.enter="submitName"
        />
        <button
          class="bg-bingo-cell text-bingo-textDark font-bold uppercase tracking-wider px-4 rounded-lg hover:brightness-110 disabled:opacity-40"
          :disabled="!inputName.trim()"
          @click="submitName"
        >
          Rejoindre
        </button>
      </div>
    </div>

    <!-- Erreur dure : bandeau rouge bloquant -->
    <div
      v-if="fatalError"
      class="bg-bingo-cellLocked/20 border border-bingo-cellLocked rounded-xl p-3 text-sm flex items-center justify-between gap-3"
    >
      <span>{{ error || 'Connexion fermée.' }}</span>
      <button
        class="text-xs px-3 py-1.5 rounded-md bg-white/10 hover:bg-white/20 uppercase tracking-wider font-semibold"
        @click="mp.connect(props.roomCode)"
      >Réessayer</button>
    </div>

    <!-- Coupure transitoire : petit badge non bloquant -->
    <div
      v-else-if="reconnecting"
      class="bg-yellow-400/15 border border-yellow-400/40 rounded-lg px-3 py-1.5 text-xs flex items-center gap-2"
    >
      <span class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
      <span class="opacity-80">Reconnexion…</span>
    </div>

    <div
      v-else-if="connStatus === 'connecting' && playerName"
      class="text-center opacity-60 py-4 text-sm"
    >Connexion à la room…</div>

    <!-- LOBBY -->
    <template v-if="serverPhase === 'lobby' && connStatus === 'connected'">
      <section class="bg-white/5 border border-white/10 rounded-xl p-4">
        <div class="text-xs uppercase tracking-widest opacity-60 mb-2">
          Participants ({{ players.length }})
        </div>
        <ul class="space-y-1.5">
          <li
            v-for="p in players"
            :key="p.id"
            class="flex items-center gap-2 text-sm"
            :class="p.connected === false ? 'opacity-50' : ''"
          >
            <span
              class="w-2 h-2 rounded-full"
              :class="p.connected === false ? 'bg-yellow-400 animate-pulse' : 'bg-bingo-cell'"
              :title="p.connected === false ? 'Déconnecté — peut revenir' : 'Connecté'"
            ></span>
            <span class="font-semibold truncate">{{ p.name }}</span>
            <span v-if="p.id === selfId" class="opacity-60 text-xs">(toi)</span>
            <span
              v-if="p.connected === false"
              class="text-[10px] uppercase tracking-wider text-yellow-400/90"
            >reconnexion…</span>
            <span
              v-if="p.id === mp.roomState?.hostId"
              class="ml-auto text-[10px] uppercase tracking-wider bg-bingo-cell/20 text-bingo-cell px-1.5 py-0.5 rounded"
            >Host</span>
          </li>
        </ul>
      </section>

      <button
        v-if="isHost"
        class="w-full bg-bingo-cell text-bingo-textDark font-bebas uppercase tracking-widest py-3 rounded-xl hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed text-xl"
        :disabled="players.length === 0"
        @click="mp.start()"
      >Lancer la partie</button>
      <p v-else class="text-center text-sm opacity-60 py-2">
        En attente du host pour lancer…
      </p>
    </template>

    <!-- PLAYING -->
    <template v-if="serverPhase === 'playing'">
      <!--
        Joueur courant + timer perso. Bleed edge-to-edge sur mobile via
        wrapper div : on NE passe PAS la classe directement à PlayerCard,
        sinon sa racine cumule `w-full` (interne) + `w-[calc(...)]`
        (externe) — deux déclarations `width` de spécificité égale, le
        gagnant dépend de l'ordre dans le CSS généré par Tailwind JIT et
        n'est pas garanti. Conséquence observée : la bande restait
        ~24px trop courte sur certains builds.
        Avec un wrapper qui porte seul `-mx-3 w-[calc(100%+1.5rem)]`,
        plus de conflit ; PlayerCard `w-full` remplit ce wrapper élargi.
      -->
      <div v-if="!isDone" class="-mx-3 w-[calc(100%+1.5rem)]">
        <PlayerCard
          :player="currentPlayer"
          :turn-index="turnIndex"
          :total-turns="sequenceLength"
          :time-left="timeLeftSeconds"
          :timer-progress="timerProgress"
          @skip="mp.skip()"
        />
      </div>

      <!--
        Tu as fini : on affiche ton score perso et un bouton qui ouvre le
        classement complet (modal). Tu n'as PAS besoin d'attendre que les
        autres aient fini pour voir où tu te situes — le bouton affiche
        en live les scores figés des joueurs déjà finis et le statut "en
        cours" pour les autres.
      -->
      <div
        v-else
        class="bg-bingo-cell/10 border border-bingo-cell/40 rounded-2xl p-4 text-center"
      >
        <div class="text-bingo-cell font-bebas uppercase tracking-widest text-xl mb-2">
          Tu as termine !
        </div>
        <div class="flex flex-col items-center mb-3">
          <span class="text-[10px] uppercase tracking-widest opacity-60">Ton score</span>
          <span class="tabular-nums font-bebas text-bingo-cell text-5xl tracking-wide leading-none">{{ myScore }}</span>
          <span class="text-[10px] opacity-50 mt-0.5">/ {{ rules.totalPerfectScore }}</span>
        </div>
        <button
          class="w-full bg-bingo-cell text-bingo-textDark font-bebas uppercase tracking-widest py-2.5 rounded-lg hover:brightness-110 text-base mb-2"
          @click="showRanking = true"
        >Voir mon classement</button>
        <div class="text-xs opacity-70">
          {{ doneCount }} / {{ totalPlayers }} ont fini
        </div>
      </div>

      <!--
        Grille style Football Bingo : edge-to-edge via -mx-3, mini-gap
        gap-px qui laisse passer le bg de la page entre les cases (effet
        "tuiles" séparées). Pas de radius wrapper, juste un fond purple
        qui sert de séparateur fin entre les cases.
      -->
      <div v-if="cells.length === 16" class="-mx-3 w-[calc(100%+1.5rem)] grid grid-cols-4 grid-rows-4 aspect-[4/4.6] gap-px bg-bingo-bg">
        <GridCell
          v-for="(cell, i) in cells"
          :key="cell.id"
          :cell="cell"
          :state="cellStates[cell.id] || { status: 'empty', playerName: null, wasCorrect: null }"
          :index="i"
          :reveal-errors="isDone"
          :disabled="cellGridDisabled"
          @click="(id) => mp.place(id)"
        />
      </div>

      <!--
        Leaderboard CACHÉ pendant la partie — on ne révèle les scores
        des autres qu'au recap final, pour préserver le focus du joueur
        sur sa propre grille.
      -->
    </template>

    <!-- ENDED -->
    <template v-if="serverPhase === 'ended'">
      <StatusBanner
        :ended="true"
        :won="won"
        :placed-count="placedCount"
        :total="rules.gridSize"
        @restart="isHost && mp.restart()"
      />

      <!--
        Pas de Leaderboard inline ici : on libère l'espace écran pour la
        grille (cases plus visibles). Le bouton "Voir le classement"
        ouvre la modal — même UX que mid-game.
      -->
      <button
        class="w-full bg-bingo-cell text-bingo-textDark font-bebas uppercase tracking-widest py-3 rounded-xl hover:brightness-110 text-xl"
        @click="showRanking = true"
      >Voir le classement</button>

      <!--
        Grille fin de partie : même layout que pendant le jeu (gap-px,
        pas de radius). La couleur des cases (lime / rouge / vide) suffit
        comme feedback, pas besoin d'introduire des gaps épais + radius.
      -->
      <div v-if="cells.length === 16" class="-mx-3 w-[calc(100%+1.5rem)] grid grid-cols-4 grid-rows-4 aspect-[4/4.6] gap-px bg-bingo-bg">
        <GridCell
          v-for="(cell, i) in cells"
          :key="cell.id"
          :cell="cell"
          :state="cellStates[cell.id] || { status: 'empty', playerName: null, wasCorrect: null }"
          :index="i"
          :reveal-errors="true"
          :disabled="true"
          @click="() => {}"
        />
      </div>

      <button
        v-if="isHost"
        class="w-full bg-bingo-cell text-bingo-textDark font-bebas uppercase tracking-widest py-3 rounded-xl hover:brightness-110 text-xl"
        @click="mp.restart()"
      >Rejouer (meme room)</button>
      <p v-else class="text-center text-sm opacity-60">En attente du host pour rejouer…</p>
    </template>

    <!--
      Modal Classement : visible quand `showRanking` est true. Affiche la
      table (Time / Pld / Pts) pour tous les joueurs. Les joueurs déjà
      finis montrent leurs scores réels figés ; les joueurs encore en
      cours sont marqués "En cours" et triés en bas.
      Backdrop avec blur, card centrée, fermeture par X ou click backdrop.
    -->
    <div
      v-if="showRanking"
      class="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-3 sm:p-6"
      @click.self="showRanking = false"
    >
      <div class="w-full max-w-md bg-bingo-bg border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-cell-stamp">
        <!-- Header modal -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <span class="font-bebas uppercase tracking-widest text-xl">Classement</span>
          <button
            class="text-white/60 hover:text-white text-2xl leading-none px-1 -mr-1"
            title="Fermer"
            @click="showRanking = false"
          >×</button>
        </div>
        <Leaderboard
          :entries="leaderboard"
          :self-id="selfId"
          :reveal="true"
          :total="rules.gridSize"
          class="border-0 rounded-none"
        />
        <div class="px-4 py-3 text-center text-xs opacity-60 border-t border-white/10">
          {{ doneCount }} / {{ totalPlayers }} joueurs ont fini
        </div>
      </div>
    </div>
  </main>
</template>
