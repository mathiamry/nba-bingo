/**
 * i18n maison — pas de dépendance lourde type vue-i18n.
 *
 * - `locale` est un ref Vue : on le lit dans le template via t(), ce qui
 *   abonne automatiquement le composant aux changements de langue.
 * - `t('foo.bar', { count: 3 })` lookup avec dot-path + interpolation {placeholder}.
 * - `translateLabel(label, axis)` traduit les libellés de cases du jeu
 *   (côté frontend, sans regénérer game.json — beaucoup plus rapide à itérer).
 * - Auto-détection au premier visit via navigator.language, override
 *   persisté en localStorage par setLocale().
 */
import { ref } from 'vue'

const STORAGE_KEY = 'nbaBingoLocale'
const FALLBACK = 'fr'
const SUPPORTED = ['fr', 'en']

function detectInitial() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (SUPPORTED.includes(stored)) return stored
    const nav = (navigator.language || '').toLowerCase()
    if (nav.startsWith('fr')) return 'fr'
    return 'en'
  } catch {
    return FALLBACK
  }
}

export const locale = ref(detectInitial())

export function setLocale(loc) {
  if (!SUPPORTED.includes(loc)) return
  locale.value = loc
  try { localStorage.setItem(STORAGE_KEY, loc) } catch { /* noop */ }
  // Met à jour <html lang="..."> pour l'accessibilité et le SEO.
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', loc)
  }
}

// Applique la lang au document au boot (pour le cas où la valeur est
// chargée depuis localStorage, donc différente du lang="fr" du HTML).
if (typeof document !== 'undefined') {
  document.documentElement.setAttribute('lang', locale.value)
}

// ─── Messages ────────────────────────────────────────────────────────────

const messages = {
  fr: {
    appTitle: 'NBA BINGO',
    common: {
      close: 'Fermer',
      cancel: 'Annuler',
      retry: 'Réessayer',
      player: 'Joueur',
      champion: 'Champion',
      score: 'Score',
      time: 'Time',
      pld: 'Pld',
      pts: 'Pts',
      live: 'Live',
      final: 'Final',
      you: 'You',
      off: 'Off',
      host: 'Host',
      skip: 'SKIP',
      left: 'LEFT',
      switchLang: 'EN',
      langLabel: 'English',
    },
    home: {
      firstNameLabel: 'Ton prénom',
      firstNamePlaceholder: 'Ex. Mathia',
      firstNameHelp: 'Visible par tes amis dans la room. Mémorisé localement pour les prochaines parties.',
      solo: 'Jouer en solo',
      createRoom: 'Creer une room',
      joinRoomLabel: 'Rejoindre une room',
      joinPlaceholder: 'NBA-XXXXX',
      joinOk: 'OK',
      tagline: 'Le mode multijoueur synchronise les joueurs proposés — tout le monde voit le même au même moment, et le récap final classe les scores.',
      legal: 'Mentions légales & confidentialité',
    },
    room: {
      back: '← Quitter',
      leave: 'Quitter la room',
      code: 'Code de la room',
      copyLink: 'Lien',
      copied: 'Copie ✓',
      joinName: 'Rejoindre',
      connecting: 'Connexion à la room…',
      connectionClosed: 'Connexion fermée.',
      reconnecting: 'Reconnexion…',
      disconnectedTooltip: 'Déconnecté — peut revenir',
      connectedTooltip: 'Connecté',
      disconnectedTag: 'reconnexion…',
      participants: 'Participants ({count})',
      you: '(toi)',
      startGame: 'Lancer la partie',
      waitingHost: 'En attente du host pour lancer…',
      youAreDone: 'Tu as terminé !',
      yourScore: 'Ton score',
      viewRanking: 'Voir mon classement',
      doneCount: '{n} / {m} ont fini',
      viewRankingEnded: 'Voir le classement',
      restart: 'Rejouer (même room)',
      waitingRestart: 'En attente du host pour rejouer…',
      rankingTitle: 'Classement',
      rankingDoneCount: '{n} / {m} joueurs ont fini',
    },
    playerCard: {
      waiting: 'EN ATTENTE',
    },
    leaderboard: {
      inProgress: 'En cours',
      finalLabel: 'Final',
      liveLabel: 'Live',
    },
    countdown: {
      tipOff: 'Tip-off dans',
      aria: 'La partie commence dans {s} secondes',
      footer: 'NBA Bingo · Multijoueur',
    },
    status: {
      bravo: 'BRAVO !',
      done: 'TERMINÉ',
      placed: 'cases posées',
      restart: 'Rejouer',
    },
    recap: {
      askName: "Comment tu t'appelles ?",
      saveHint: 'On garde ton nom pour les prochaines parties.',
      namePlaceholder: 'Ton prénom',
      showScore: 'Voir mon score',
      editName: 'modifier',
      editTooltip: 'Modifier le nom',
      cellsAndErrorsSingular: '{placed}/{total} cases · {errors} erreur',
      cellsAndErrorsPlural: '{placed}/{total} cases · {errors} erreurs',
      viewGrid: 'Voir la grille',
    },
    solo: {
      banner: 'Mode solo — {seconds}s par tour, grille parfaite : {score} pts.',
      loading: 'Chargement…',
      errorTitle: 'Impossible de charger la partie : {err}.',
      errorHint: 'Lance {cmd} pour générer {file}.',
    },
    legal: {
      back: '← Retour',
      mentionsTitle: 'Mentions légales',
      mentionsP1: "NBA Bingo est un projet personnel développé par {name} et hébergé sur l'infrastructure PartyKit (Cloudflare Workers).",
      mentionsP2: 'Le code source est public sur GitHub. Pour toute question, signaler un bug ou demander la suppression de données, ouvre une issue sur le dépôt.',
      mentionsP3: "Le jeu est fourni « tel quel », à but ludique et gratuit. Aucune garantie d'exactitude des données NBA ou de disponibilité du service.",
      privacyTitle: 'Confidentialité',
      privacyIntro: 'On essaye de collecter le strict minimum. Voici ce qui est stocké et où :',
      privacyLocalTitle: 'Sur ton appareil (localStorage)',
      privacyLocal1: 'Ton pseudo (24 caractères max)',
      privacyLocal2: "Un identifiant de session aléatoire (UUID), utilisé pour que tu retrouves ta place si tu changes d'onglet ou que ta connexion saute",
      privacyLocalHintBefore: 'Pour effacer : Réglages navigateur → Données de site → vider. Ou tape ',
      privacyLocalHintAfter: ' dans la console.',
      privacyServerTitle: 'Sur le serveur (en mémoire uniquement)',
      privacyServer1: 'Ton pseudo + ton identifiant de session, le temps de la partie multijoueur',
      privacyServer2: 'Tes placements et ton score, pour le leaderboard',
      privacyServerHint: "Ces données sont effacées automatiquement quand la room se vide. Rien n'est persisté en base ni partagé avec un tiers.",
      privacyAnalyticsTitle: 'Mesure d\'audience anonyme',
      privacyAnalytics: "On utilise Cloudflare Web Analytics et Plausible pour compter les visites et les parties jouées. Aucun cookie n'est posé, aucune adresse IP n'est stockée individuellement, aucun fingerprinting. Les seules métriques collectées sont agrégées : nombre de visiteurs uniques par jour, pays, type d'appareil, événements game_started / game_finished avec compteur de joueurs et score moyen.",
      privacyFooter: 'Pas de cookies, pas de trackers publicitaires, pas de pub.',
      creditsTitle: 'Crédits',
      creditsBody: "Données joueurs et statistiques : nba_api (basé sur stats.nba.com). Logos des franchises : marques déposées de la NBA, utilisés à titre informatif uniquement. NBA Bingo n'est ni affilié, ni sponsorisé, ni approuvé par la NBA.",
    },
  },
  en: {
    appTitle: 'NBA BINGO',
    common: {
      close: 'Close',
      cancel: 'Cancel',
      retry: 'Retry',
      player: 'Player',
      champion: 'Champion',
      score: 'Score',
      time: 'Time',
      pld: 'Pld',
      pts: 'Pts',
      live: 'Live',
      final: 'Final',
      you: 'You',
      off: 'Off',
      host: 'Host',
      skip: 'SKIP',
      left: 'LEFT',
      switchLang: 'FR',
      langLabel: 'Français',
    },
    home: {
      firstNameLabel: 'Your name',
      firstNamePlaceholder: 'e.g. Mathia',
      firstNameHelp: 'Visible to friends in your room. Saved locally for future sessions.',
      solo: 'Play solo',
      createRoom: 'Create a room',
      joinRoomLabel: 'Join a room',
      joinPlaceholder: 'NBA-XXXXX',
      joinOk: 'OK',
      tagline: 'Multiplayer syncs the player sequence — everyone sees the same one at the same time, and the final recap ranks scores.',
      legal: 'Legal notice & privacy',
    },
    room: {
      back: '← Leave',
      leave: 'Leave room',
      code: 'Room code',
      copyLink: 'Link',
      copied: 'Copied ✓',
      joinName: 'Join',
      connecting: 'Connecting to the room…',
      connectionClosed: 'Connection closed.',
      reconnecting: 'Reconnecting…',
      disconnectedTooltip: 'Disconnected — may return',
      connectedTooltip: 'Connected',
      disconnectedTag: 'reconnecting…',
      participants: 'Participants ({count})',
      you: '(you)',
      startGame: 'Start the game',
      waitingHost: 'Waiting for the host to start…',
      youAreDone: "You're done!",
      yourScore: 'Your score',
      viewRanking: 'View ranking',
      doneCount: '{n} / {m} finished',
      viewRankingEnded: 'View ranking',
      restart: 'Play again (same room)',
      waitingRestart: 'Waiting for host to restart…',
      rankingTitle: 'Ranking',
      rankingDoneCount: '{n} / {m} players finished',
    },
    playerCard: {
      waiting: 'WAITING',
    },
    leaderboard: {
      inProgress: 'In progress',
      finalLabel: 'Final',
      liveLabel: 'Live',
    },
    countdown: {
      tipOff: 'Tip-off in',
      aria: 'Game starts in {s} seconds',
      footer: 'NBA Bingo · Multiplayer',
    },
    status: {
      bravo: 'WELL DONE!',
      done: 'DONE',
      placed: 'cells placed',
      restart: 'Play again',
    },
    recap: {
      askName: "What's your name?",
      saveHint: "We'll keep your name for future sessions.",
      namePlaceholder: 'Your name',
      showScore: 'View my score',
      editName: 'edit',
      editTooltip: 'Edit name',
      cellsAndErrorsSingular: '{placed}/{total} cells · {errors} error',
      cellsAndErrorsPlural: '{placed}/{total} cells · {errors} errors',
      viewGrid: 'View grid',
    },
    solo: {
      banner: 'Solo mode — {seconds}s per turn, perfect score: {score} pts.',
      loading: 'Loading…',
      errorTitle: 'Failed to load the game: {err}.',
      errorHint: 'Run {cmd} to generate {file}.',
    },
    legal: {
      back: '← Back',
      mentionsTitle: 'Legal notice',
      mentionsP1: 'NBA Bingo is a personal project built by {name} and hosted on the PartyKit infrastructure (Cloudflare Workers).',
      mentionsP2: 'The source code is public on GitHub. For any question, bug report, or data deletion request, open an issue on the repo.',
      mentionsP3: 'The game is provided "as is", for fun and free. No warranty on NBA data accuracy or service availability.',
      privacyTitle: 'Privacy',
      privacyIntro: "We try to collect as little as possible. Here's what's stored and where:",
      privacyLocalTitle: 'On your device (localStorage)',
      privacyLocal1: 'Your name (max 24 characters)',
      privacyLocal2: "A random session ID (UUID), used so you can pick up where you left off if you switch tabs or your connection drops",
      privacyLocalHintBefore: 'To clear: Browser settings → Site data → wipe. Or type ',
      privacyLocalHintAfter: ' in the console.',
      privacyServerTitle: 'On the server (in-memory only)',
      privacyServer1: 'Your name + session ID, only during a multiplayer match',
      privacyServer2: 'Your placements and score, for the leaderboard',
      privacyServerHint: "These are wiped automatically when the room empties. Nothing is persisted to a database or shared with any third party.",
      privacyAnalyticsTitle: 'Anonymous audience measurement',
      privacyAnalytics: "We use Cloudflare Web Analytics and Plausible to count visits and games played. No cookies are set, no IP address is stored individually, no fingerprinting. The only metrics collected are aggregated: unique visitors per day, country, device type, game_started / game_finished events with player count and average score.",
      privacyFooter: 'No cookies, no ad trackers, no ads.',
      creditsTitle: 'Credits',
      creditsBody: "Player data and stats: nba_api (based on stats.nba.com). Franchise logos: NBA trademarks, used for informational purposes only. NBA Bingo is neither affiliated with, nor endorsed by, the NBA.",
    },
  },
}

function getPath(obj, path) {
  return path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj)
}

export function t(key, params) {
  // Lecture de locale.value pour s'abonner à la réactivité.
  const dict = messages[locale.value] || messages[FALLBACK]
  let str = getPath(dict, key)
  if (str === undefined) {
    str = getPath(messages[FALLBACK], key)
  }
  if (typeof str !== 'string') return key
  if (params) {
    for (const k in params) {
      str = str.replace(new RegExp(`\\{${k}\\}`, 'g'), params[k])
    }
  }
  return str
}

// ─── Catégories du jeu ───────────────────────────────────────────────────
//
// On traduit côté client à l'affichage, sans régénérer game.json. Si une
// catégorie n'a pas de traduction dans la table, on retombe sur le libellé
// FR — toujours mieux que vide.

const CATEGORY_MAP = {
  TEAM: {
    'Hornets de La Nouvelle-Orléans': 'New Orleans Hornets',
    'Nets du New Jersey': 'New Jersey Nets',
    'SuperSonics de Seattle': 'Seattle SuperSonics',
    // Les autres noms d'équipes (Lakers, Bulls, Knicks, etc.) restent
    // identiques en EN — pas la peine de les lister.
  },
  NATIONALITY: {
    Allemagne: 'Germany',
    Australie: 'Australia',
    Cameroun: 'Cameroon',
    Canada: 'Canada',
    Croatie: 'Croatia',
    Espagne: 'Spain',
    France: 'France',
    'Grande-Bretagne': 'Great Britain',
    Italie: 'Italy',
    Lituanie: 'Lithuania',
    Serbie: 'Serbia',
    Slovénie: 'Slovenia',
  },
  AWARD: {
    'Argent JO 2024': '2024 Olympic Silver',
    'Or JO 2024': '2024 Olympic Gold',
    'MVP + Finals MVP + champion': 'MVP + Finals MVP + champion',
    'ROY + champion': 'ROY + champion',
  },
  CAREER: {
    '1 seule franchise': '1 franchise only',
    '4+ franchises': '4+ franchises',
    'Champion NBA': 'NBA Champion',
  },
  DRAFT: {
    '2e tour + All-Star': '2nd round + All-Star',
    '2e tour + champion': '2nd round + champion',
    '2e tour de draft': '2nd round draft pick',
    'Draft #1': '#1 draft pick',
    'Top 3 draft': 'Top 3 draft pick',
  },
  ERA: {
    'Années 2000': '2000s',
    'Années 2020': '2020s',
    'Années 90': '90s',
  },
  STAT: {
    '20+ PPG et 8+ AST': '20+ PPG and 8+ APG',
    // 10+ RPG, 20+ PPG, 25+ PPG, 8+ APG sont déjà universels.
  },
  // TEAMMATE est templated : "Joué avec X" → "Played with X". Géré
  // séparément dans translateLabel().
}

export function translateLabel(label, axis) {
  if (locale.value === 'fr') return label
  if (!label || !axis) return label
  if (axis === 'TEAMMATE' && label.startsWith('Joué avec ')) {
    return 'Played with ' + label.slice('Joué avec '.length)
  }
  const map = CATEGORY_MAP[axis]
  if (map && map[label] != null) return map[label]
  return label
}
