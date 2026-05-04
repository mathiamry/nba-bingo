"""
Recalcule career_ppg / career_rpg / career_apg via nba_api
`playercareerstats` pour TOUS les joueurs du pool. Élimine le gap
2023-24 entre nos deux CSVs (saison 2023-24 entièrement absente,
fausse les moyennes des actifs comme CP3, Klay, Boogie).

Usage :
    .venv/bin/python enrich_career_stats.py [--sleep 0.7]

Sortie : `nba_dataset_extracted/live_career_stats.json` au format
    {
      "fetched_at": "...",
      "season": "career-stats",
      "rosters": {},
      "player_info": {},
      "player_awards": {},
      "player_career_stats": {
        "<pid>": {"gp": 1419, "pts": 39064, "reb": 11211, "ast": 8857}
      }
    }

Le loader divise les totaux par GP pour obtenir les averages, qui
overridé les valeurs CSV agrégées dans le Player.
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


def fetch_totals(playercareerstats_mod, pid: int, retries: int = 2):
    """Somme PTS/REB/AST/GP sur toutes les saisons hors TOT mid-season."""
    for attempt in range(retries + 1):
        try:
            res = playercareerstats_mod.PlayerCareerStats(
                player_id=pid, timeout=20,
            ).get_normalized_dict()
            rows = res.get("SeasonTotalsRegularSeason", []) or []
            gp = pts = reb = ast = 0
            for r in rows:
                # Skip "TOT" rows — agrégat mid-season qu'on doublerait sinon
                if (r.get("TEAM_ABBREVIATION") or "") == "TOT":
                    continue
                try:
                    gp += int(r.get("GP") or 0)
                    pts += int(r.get("PTS") or 0)
                    reb += int(r.get("REB") or 0)
                    ast += int(r.get("AST") or 0)
                except (ValueError, TypeError):
                    pass
            if gp == 0:
                return None
            return {"gp": gp, "pts": pts, "reb": reb, "ast": ast}
        except Exception as e:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=0.7)
    parser.add_argument("--out", default="nba_dataset_extracted/live_career_stats.json")
    args = parser.parse_args()

    playercareerstats_mod = _import_nba_api()

    from nba_dataset_loader import load_real_dataset
    cats, players = load_real_dataset("nba_dataset_extracted")
    print(f"📊 Pool : {len(players)} joueurs")
    print(f"📥 Fetch career totals (~{len(players) * args.sleep:.0f}s)…")

    out_stats: dict[str, dict] = {}

    for i, p in enumerate(players, 1):
        totals = fetch_totals(playercareerstats_mod, p.id)
        if totals:
            out_stats[str(p.id)] = totals
        time.sleep(args.sleep)

        if i % 25 == 0 or i == len(players):
            print(f"  {i:3d}/{len(players)}  ({len(out_stats)} avec stats)")

    out = {
        "fetched_at": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "season": "career-stats",
        "rosters": {},
        "player_info": {},
        "player_awards": {},
        "player_career_stats": out_stats,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n✅ {len(out_stats)} joueurs → {args.out}")


if __name__ == "__main__":
    main()
