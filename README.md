# NBA Bingo

Adaptation NBA du jeu [Football Bingo](https://playfootball.games/football-bingo).
Une grille 4x4 de catégories (équipes, awards, nationalités, stats, "a joué avec X"…) que tu remplis en plaçant des joueurs NBA proposés un par un.

## Règles

- Grille 4x4 (16 cases), pas de case libre.
- Un joueur est proposé toutes les 10s. À toi de le placer dans une case valide.
- Mauvaise case = la case reste verte… **jusqu'à la fin** où elle passe en rouge (révélation tardive).
- Score : grille parfaite = **60 pts** (3.75 pts par case).

## Modes

- **Solo** — `#/solo`. Une partie aléatoire piochée dans le pool, score local.
- **Multijoueur (room)** — `#/r/CODE`. Le host crée une room, partage le code (ou le lien `…#/r/NBA-XXXX`). Tout le monde voit le même joueur proposé au même moment, le serveur arbitre les turns (10s ou tous ont placé), leaderboard live (cases posées), score révélé à la fin.

## Stack

- **Python 3.11** — générateur de grille (CSP backtracking + matching biparti pour la séquence partagée).
- **Vue 3 + Vite + Pinia + Tailwind** — frontend.
- **PartyKit (Cloudflare Workers + Durable Objects)** — serveur multijoueur temps réel, dans `partykit/`.
- **Nginx** — runtime du frontend en prod.

## Quick start (Docker)

```bash
docker compose up -d
# http://localhost:8080
```

Le build Docker enchaîne :
1. **Python** lit `nba_dataset_extracted/` (CSV NBA 2024-25, 490 joueurs, 73 catégories) et écrit 20 parties dans `frontend/public/game.json`.
2. **Vite** build le SPA en intégrant le JSON.
3. **Nginx** sert les fichiers statiques.

## Dev local

### Solo seulement
```bash
# 1. Génère 20 parties (frontend/public/game.json + partykit/src/games.json)
python3 nba_bingo_grid.py

# 2. Lance Vite
cd frontend && npm install && npm run dev
# http://localhost:5173
```

### Solo + multijoueur
Trois terminaux :
```bash
# Terminal 1 — génère les parties
python3 nba_bingo_grid.py

# Terminal 2 — serveur PartyKit (nécessite Node ≥ 22, .nvmrc fourni)
cd partykit && nvm use && npm install && npm run dev
# http://127.0.0.1:1999

# Terminal 3 — frontend Vite
cd frontend && npm install && npm run dev
# http://localhost:5173
```

Le frontend lit `VITE_PARTYKIT_HOST` (défaut `127.0.0.1:1999`). Copie `frontend/.env.example` → `frontend/.env` pour overrider.

### Déployer le serveur multijoueur sur Cloudflare
```bash
cd partykit
npm run deploy   # première fois : connexion Cloudflare via le navigateur
```
Ça donne une URL type `https://nba-bingo.<pseudo>.partykit.dev`. Builde le frontend avec :
```bash
VITE_PARTYKIT_HOST=nba-bingo.<pseudo>.partykit.dev docker compose up -d --build
```

Pour rafraîchir le pool de parties, relance la commande Python.

## Structure

```
.
├── nba_bingo_grid.py          générateur générique (quotas, CSP, séquence)
├── nba_dataset_loader.py      loader du dataset 2024-25 + enrichissements
├── nba_dataset_extracted/     CSV (NBA_PLAYERS, NBA_TEAMS, NBA_PLAYER_GAMES)
├── frontend/                  Vue 3 + Vite + Tailwind + Pinia
│   ├── public/game.json       artefact généré (gitignored)
│   └── src/
│       ├── App.vue
│       ├── stores/game.js     état partie + timer + score
│       └── components/
│           ├── GridCell.vue
│           ├── PlayerCard.vue
│           ├── StatusBanner.vue
│           └── RecapModal.vue
├── partykit/                  serveur multijoueur (Cloudflare Workers)
│   ├── partykit.json
│   └── src/
│       ├── server.ts          lobby → playing → ended, timer 10s autoritaire
│       └── games.json         pool partagé (gitignored, copié par Python)
├── Dockerfile                 multi-stage Python → Node → Nginx
├── nginx.conf
└── docker-compose.yml
```

## Données

- **Joueurs / équipes / matchs 2024-25** dérivés des CSV du dataset.
- **Awards / nationalité / draft** enrichis manuellement pour ~50 stars dans `nba_dataset_loader.py`.
- Pour étendre : ajouter une entrée à `ENRICHMENT_BY_NAME` (clé = nom EXACT du CSV, avec diacritiques type `Dončić`).
