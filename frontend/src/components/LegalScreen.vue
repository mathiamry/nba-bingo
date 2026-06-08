<script setup>
defineEmits(['back'])
</script>

<template>
  <main class="w-full max-w-2xl px-4 mt-6 mb-10 flex flex-col gap-6 text-sm leading-relaxed">
    <button
      type="button"
      class="self-start text-xs uppercase tracking-widest opacity-70 hover:opacity-100"
      @click="$emit('back')"
    >
      ← Retour
    </button>

    <section class="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col gap-3">
      <h2 class="text-xl font-semibold">Mentions légales</h2>
      <p>
        NBA Bingo est un projet personnel développé par
        <strong>Elhadji Mamadou Thiam</strong> et hébergé sur l'infrastructure
        <a
          href="https://www.partykit.io"
          target="_blank"
          rel="noopener noreferrer"
          class="underline"
        >PartyKit</a>
        (Cloudflare Workers).
      </p>
      <p>
        Le code source est public sur
        <a
          href="https://github.com/mathiamry/nba-bingo"
          target="_blank"
          rel="noopener noreferrer"
          class="underline"
        >GitHub</a>.
        Pour toute question, signaler un bug ou demander la suppression
        de données, ouvre une issue sur le dépôt.
      </p>
      <p>
        Le jeu est fourni « tel quel », à but ludique et gratuit. Aucune
        garantie d'exactitude des données NBA ou de disponibilité du
        service.
      </p>
    </section>

    <section class="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col gap-3">
      <h2 class="text-xl font-semibold">Confidentialité</h2>
      <p class="opacity-90">
        On essaye de collecter le strict minimum. Voici ce qui est stocké
        et où :
      </p>

      <div class="bg-black/30 rounded-xl p-4 flex flex-col gap-2">
        <p>
          <strong>Sur ton appareil (localStorage)</strong>
        </p>
        <ul class="list-disc list-inside space-y-1 opacity-90">
          <li>Ton pseudo (24 caractères max)</li>
          <li>Un identifiant de session aléatoire (UUID), utilisé pour
            que tu retrouves ta place si tu changes d'onglet ou que ta
            connexion saute</li>
        </ul>
        <p class="text-xs opacity-70 mt-1">
          Pour effacer : Réglages navigateur → Données de site → vider.
          Ou tape <code class="bg-black/40 px-1 rounded">localStorage.clear()</code>
          dans la console.
        </p>
      </div>

      <div class="bg-black/30 rounded-xl p-4 flex flex-col gap-2">
        <p>
          <strong>Sur le serveur (en mémoire uniquement)</strong>
        </p>
        <ul class="list-disc list-inside space-y-1 opacity-90">
          <li>Ton pseudo + ton identifiant de session, le temps de la
            partie multijoueur</li>
          <li>Tes placements et ton score, pour le leaderboard</li>
        </ul>
        <p class="text-xs opacity-70 mt-1">
          Ces données sont effacées automatiquement quand la room se
          vide. Rien n'est persisté en base ni partagé avec un tiers.
        </p>
      </div>

      <p class="text-xs opacity-70">
        Pas de cookies, pas de trackers, pas d'analytics, pas de pub.
      </p>
    </section>

    <section class="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col gap-3">
      <h2 class="text-xl font-semibold">Crédits</h2>
      <p class="opacity-90">
        Données joueurs et statistiques :
        <a
          href="https://github.com/swar/nba_api"
          target="_blank"
          rel="noopener noreferrer"
          class="underline"
        >nba_api</a>
        (basé sur stats.nba.com).
        Logos des franchises : marques déposées de la NBA, utilisés à
        titre informatif uniquement. NBA Bingo n'est ni affilié, ni
        sponsorisé, ni approuvé par la NBA.
      </p>
    </section>
  </main>
</template>
