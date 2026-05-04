"""
Enrichit awards + info pour TOUS les joueurs du pool, pas seulement
ceux des rosters 2025-26. Fix les cas où un retraité (Richard Jefferson,
Amar'e Stoudemire, JJ Redick, Mo Williams…) avait awards/draft/champion
vides parce que ni `fetch_live_data.py` ni `ENRICHMENT_BY_NAME` ne les
couvrait.

Usage :
    .venv/bin/python enrich_pool.py [--sleep 0.7]

Le script :
1. Charge le pool actuel (~250 joueurs après filtre fame_score).
2. Skip les joueurs déjà enrichis (awards ou nationalité non vides).
3. Fetch commonplayerinfo + playerawards pour les autres.
4. Écrit `nba_dataset_extracted/live_pool_enriched.json`.
   Le loader merge ce snapshot comme n'importe quel autre `live_*.json`.

Compter ~5 min pour 170 joueurs × 2 calls × 0.7s.
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
        from nba_api.stats.endpoints import commonplayerinfo, playerawards
        return commonplayerinfo, playerawards
    except ImportError as e:
        print(f"❌ nba_api introuvable : {e}")
        sys.exit(1)


def fetch_info(commonplayerinfo_mod, pid: int, retries: int = 2):
    for attempt in range(retries + 1):
        try:
            res = commonplayerinfo_mod.CommonPlayerInfo(
                player_id=pid, timeout=20,
            ).get_normalized_dict()
            row = (res.get("CommonPlayerInfo") or [{}])[0]
            return {
                "player_id": pid,
                "country": row.get("COUNTRY") or "",
                "draft_year": row.get("DRAFT_YEAR") or None,
                "draft_round": row.get("DRAFT_ROUND") or None,
                "draft_number": row.get("DRAFT_NUMBER") or None,
                "from_year": row.get("FROM_YEAR") or None,
                "to_year": row.get("TO_YEAR") or None,
            }
        except Exception as e:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return None


def fetch_awards(playerawards_mod, pid: int, retries: int = 2):
    for attempt in range(retries + 1):
        try:
            res = playerawards_mod.PlayerAwards(
                player_id=pid, timeout=20,
            ).get_normalized_dict()
            rows = res.get("PlayerAwards", []) or []
            return [
                {
                    "description": r.get("DESCRIPTION", ""),
                    "season": r.get("SEASON", ""),
                    "team": r.get("ALL_NBA_TEAM_NUMBER", ""),
                }
                for r in rows
            ]
        except Exception as e:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=0.7,
                        help="Pause entre requêtes (s).")
    parser.add_argument("--out", default="nba_dataset_extracted/live_pool_enriched.json")
    parser.add_argument("--season", default="pool",
                        help="Étiquette saison du snapshot (informatif).")
    args = parser.parse_args()

    commonplayerinfo_mod, playerawards_mod = _import_nba_api()

    # Charge le pool ACTUEL — celui-ci a déjà absorbé les snapshots
    # existants, donc les joueurs avec awards non vides n'ont plus
    # besoin d'être refetchés.
    from nba_dataset_loader import load_real_dataset
    cats, players = load_real_dataset("nba_dataset_extracted")
    print(f"📊 Pool actuel : {len(players)} joueurs")

    todo = [p for p in players if not p.awards and not p.nationality]
    print(f"📥 À enrichir : {len(todo)} joueurs "
          f"(~{len(todo) * args.sleep * 2:.0f}s)")

    player_info: dict[str, dict] = {}
    player_awards: dict[str, list] = {}

    for i, p in enumerate(todo, 1):
        info = fetch_info(commonplayerinfo_mod, p.id)
        if info:
            player_info[str(p.id)] = info
        time.sleep(args.sleep)

        awards = fetch_awards(playerawards_mod, p.id)
        if awards is not None:
            player_awards[str(p.id)] = awards
        time.sleep(args.sleep)

        if i % 10 == 0 or i == len(todo):
            n_aw = sum(1 for v in player_awards.values() if v)
            print(f"  {i:3d}/{len(todo)}  ({n_aw} avec ≥1 award)")

    out = {
        "fetched_at": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "season": args.season,
        "rosters": {},  # vide : ce snapshot ne sert qu'à enrichir info/awards
        "player_info": player_info,
        "player_awards": player_awards,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    n_aw = sum(1 for v in player_awards.values() if v)
    print(f"\n✅ {len(player_info)} infos + {n_aw} awards écrits dans {args.out}")


if __name__ == "__main__":
    main()
