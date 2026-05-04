"""
Reconstruit les `team_seasons` de chaque joueur via nba_api
`playercareerstats`. Cet endpoint renvoie le détail saison-par-saison
ET équipe-par-équipe — beaucoup plus précis que nos CSV qui :
  - s'arrêtent à 2022-23 pour l'historique (CP3 a manqué GSW 2023-24)
  - aggrègent parfois plusieurs équipes mid-season (Cousins MIL+HOU 2020-21)

Usage :
    .venv/bin/python enrich_career_teams.py [--sleep 0.7]

Sortie : `nba_dataset_extracted/live_career_teams.json` au format :
    {
      "fetched_at": "...",
      "season": "career",
      "rosters": {},
      "player_info": {},
      "player_awards": {},
      "player_team_seasons": {
        "<pid>": [["GSW", 2023], ["SAS", 2024], ...]
      }
    }

Le loader applique ensuite ces (team, year) en plus des CSV.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time

NBA_API_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "nba_api-master",
    "src",
)
if os.path.isdir(NBA_API_PATH):
    sys.path.insert(0, NBA_API_PATH)


def _import_nba_api():
    try:
        from nba_api.stats.endpoints import playercareerstats
        return playercareerstats
    except ImportError as e:
        print(f"❌ nba_api introuvable : {e}")
        sys.exit(1)


def fetch_career(playercareerstats_mod, pid: int, retries: int = 2):
    for attempt in range(retries + 1):
        try:
            res = playercareerstats_mod.PlayerCareerStats(
                player_id=pid, timeout=20,
            ).get_normalized_dict()
            rows = res.get("SeasonTotalsRegularSeason", []) or []
            seasons: list[tuple[str, int]] = []
            for r in rows:
                abbr = r.get("TEAM_ABBREVIATION") or ""
                # SEASON_ID format "2003-04" → on garde les 4 PREMIERS chars
                season_id = str(r.get("SEASON_ID") or "")
                try:
                    year = int(season_id[:4])
                except ValueError:
                    continue
                if abbr and abbr != "TOT":
                    # "TOT" = totaux mid-season (combinaison de plusieurs
                    # équipes), à ignorer car on veut CHAQUE équipe
                    seasons.append([abbr, year])
            return seasons
        except Exception as e:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=0.7)
    parser.add_argument("--out", default="nba_dataset_extracted/live_career_teams.json")
    args = parser.parse_args()

    playercareerstats_mod = _import_nba_api()

    from nba_dataset_loader import load_real_dataset
    cats, players = load_real_dataset("nba_dataset_extracted")
    print(f"📊 Pool actuel : {len(players)} joueurs")
    print(f"📥 Fetch career teams (~{len(players) * args.sleep:.0f}s)…")

    player_team_seasons: dict[str, list] = {}

    for i, p in enumerate(players, 1):
        seasons = fetch_career(playercareerstats_mod, p.id)
        if seasons:
            player_team_seasons[str(p.id)] = seasons
        time.sleep(args.sleep)

        if i % 25 == 0 or i == len(players):
            n_filled = sum(1 for v in player_team_seasons.values() if v)
            print(f"  {i:3d}/{len(players)}  ({n_filled} avec ≥1 saison)")

    out = {
        "fetched_at": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "season": "career",
        "rosters": {},
        "player_info": {},
        "player_awards": {},
        "player_team_seasons": player_team_seasons,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n✅ {len(player_team_seasons)} joueurs enrichis → {args.out}")


if __name__ == "__main__":
    main()
