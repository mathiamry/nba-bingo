"""
Met à jour les données NBA en piochant la saison en cours via nba_api.

Le `nba-dataset.zip` est figé sur 2024-25 — toute signature ou trade
postérieur (Seth Curry → GSW pour 2025-26 par exemple) y est absent.
Ce script appelle stats.nba.com (via nba_api) pour récupérer :

1. Les rosters de chaque équipe pour la saison spécifiée (30 calls)
2. Optionnellement, les infos persos par joueur (country, draft) — bcp
   plus de calls, désactivé par défaut.

Sortie : nba_dataset_extracted/live_<season>.json
À ré-exécuter périodiquement pour rester à jour. Le loader fusionne
ce fichier avec les CSV au démarrage.

Usage :
    .venv/bin/python fetch_live_data.py [--season 2025-26] [--with-info]

Rate limits stats.nba.com : compter 0.6-1s entre chaque call pour
éviter les 429 / blocages temporaires.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from typing import Optional

# Rend nba_api importable depuis le zip extrait sans installation pip.
NBA_API_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "nba_api-master",
    "src",
)
if os.path.isdir(NBA_API_PATH):
    sys.path.insert(0, NBA_API_PATH)


def _import_nba_api():
    try:
        from nba_api.stats.endpoints import commonteamroster, commonplayerinfo
        from nba_api.stats.static import teams
        return commonteamroster, commonplayerinfo, teams
    except ImportError as e:
        print(f"❌ nba_api introuvable. Vérifie que nba_api-master/src existe.")
        print(f"   Détail : {e}")
        sys.exit(1)


def fetch_rosters(commonteamroster_mod, teams_mod, season: str, sleep: float = 0.7):
    """Récupère le roster officiel de chaque équipe NBA pour `season`."""
    nba_teams = teams_mod.get_teams()
    rosters: dict[str, list[dict]] = {}
    print(f"📥 Fetch rosters {season} (30 équipes)…")
    for i, team in enumerate(nba_teams, 1):
        team_id = team["id"]
        abbr = team["abbreviation"]
        try:
            res = commonteamroster_mod.CommonTeamRoster(
                team_id=team_id, season=season, timeout=20,
            ).get_normalized_dict()
            entries = []
            for p in res.get("CommonTeamRoster", []):
                entries.append({
                    "player_id": int(p["PLAYER_ID"]),
                    "name": p["PLAYER"],
                    "position": p.get("POSITION", ""),
                    "birth_date": p.get("BIRTH_DATE", ""),
                    "country": p.get("BIRTH_COUNTRY") or "",
                    "exp": p.get("EXP", ""),
                })
            rosters[abbr] = entries
            print(f"  {i:2d}/30  {abbr}  ({len(entries):2d} joueurs)")
        except Exception as e:
            print(f"  {i:2d}/30  {abbr}  ✗ {type(e).__name__}: {e}")
            rosters[abbr] = []
        time.sleep(sleep)
    return rosters


def fetch_player_info(commonplayerinfo_mod, player_id: int, retries: int = 2) -> Optional[dict]:
    """Récupère country / draft / nationalité pour un joueur."""
    for attempt in range(retries + 1):
        try:
            res = commonplayerinfo_mod.CommonPlayerInfo(
                player_id=player_id, timeout=20,
            ).get_normalized_dict()
            info = (res.get("CommonPlayerInfo") or [{}])[0]
            return {
                "player_id": player_id,
                "country": info.get("COUNTRY") or "",
                "draft_year": info.get("DRAFT_YEAR") or None,
                "draft_round": info.get("DRAFT_ROUND") or None,
                "draft_number": info.get("DRAFT_NUMBER") or None,
                "from_year": info.get("FROM_YEAR") or None,
                "to_year": info.get("TO_YEAR") or None,
            }
        except Exception as e:
            if attempt < retries:
                time.sleep(1.5)
                continue
            print(f"    ✗ player {player_id}: {e}")
            return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2025-26",
                        help="Saison à fetcher (format YYYY-YY).")
    parser.add_argument("--with-info", action="store_true",
                        help="Fetch aussi country/draft par joueur (long).")
    parser.add_argument("--sleep", type=float, default=0.7,
                        help="Pause entre requêtes (secondes).")
    args = parser.parse_args()

    commonteamroster_mod, commonplayerinfo_mod, teams_mod = _import_nba_api()

    rosters = fetch_rosters(commonteamroster_mod, teams_mod, args.season, args.sleep)
    total = sum(len(v) for v in rosters.values())
    print(f"\n✅ {total} entrées roster fetchées pour {args.season}.")

    player_info: dict[str, dict] = {}
    if args.with_info:
        unique_pids = sorted({
            p["player_id"]
            for plist in rosters.values()
            for p in plist
        })
        print(f"\n📥 Fetch metadata par joueur ({len(unique_pids)} joueurs, ~{len(unique_pids)*args.sleep:.0f}s)…")
        for i, pid in enumerate(unique_pids, 1):
            info = fetch_player_info(commonplayerinfo_mod, pid)
            if info:
                player_info[str(pid)] = info
            if i % 25 == 0:
                print(f"  {i}/{len(unique_pids)}")
            time.sleep(args.sleep)

    out = {
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "season": args.season,
        "rosters": rosters,
        "player_info": player_info,
    }
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "nba_dataset_extracted",
        f"live_{args.season.replace('-', '')}.json",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Snapshot écrit dans {out_path}")


if __name__ == "__main__":
    main()
