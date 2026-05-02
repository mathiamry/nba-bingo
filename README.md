# NBA Bingo

Adaptation NBA du jeu [Football Bingo](https://playfootball.games/football-bingo).
Une grille 4x4 de catégories (équipes, awards, nationalités, stats, "a joué avec X"…) que tu remplis en plaçant des joueurs NBA proposés un par un.

## Règles

- Grille 4x4 (16 cases), pas de case libre.
- Un joueur est proposé toutes les 10s. À toi de le placer dans une case valide.
- Mauvaise case = la case reste verte… **jusqu'à la fin** où elle passe en rouge (révélation tardive).
- Score : grille parfaite = **60 pts** (3.75 pts par case).
- Mode multijoueur synchrone : tous les joueurs d'une room voient la même séquence dans le même ordre.

## Stack

- **Python 3.11** — générateur de grille (CSP backtracking + matching biparti pour la séquence partagée).
- **Vue 3 + Vite + Pinia + Tailwind** — frontend.
- **Nginx** — runtime en prod.

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

```bash
# 1. Génère 20 parties dans frontend/public/game.json
python3 nba_bingo_grid.py

# 2. Lance Vite en mode dev
cd frontend
npm install
npm run dev
# http://localhost:5173
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
├── Dockerfile                 multi-stage Python → Node → Nginx
├── nginx.conf
└── docker-compose.yml
```

## Données

- **Joueurs / équipes / matchs 2024-25** dérivés des CSV du dataset.
- **Awards / nationalité / draft** enrichis manuellement pour ~50 stars dans `nba_dataset_loader.py`.
- Pour étendre : ajouter une entrée à `ENRICHMENT_BY_NAME` (clé = nom EXACT du CSV, avec diacritiques type `Dončić`).
