"""
Correction agent for NBA Bingo — audits and optionally fixes validCellIds
in game.json against ground-truth data from the NBA API.

Usage:
  python correction_agent.py --game frontend/public/game.json          # audit
  python correction_agent.py --game frontend/public/game.json --fix    # fix
  python correction_agent.py --game frontend/public/game.json --player "Seth Curry"

How it works:
  1. Loads game.json.
  2. Calls load_dataset_from_api() to rebuild every Category predicate from
     fresh (or cached) NBA API data.
  3. For every player in every game sequence, recomputes which of that game's
     9 cells the player actually satisfies.
  4. Compares the recomputed set against the stored validCellIds and reports:
       - false negatives: cells the player satisfies but that were missing
       - false positives: cells stored as valid but that the player does not satisfy
  5. With --fix, overwrites game.json with the corrected validCellIds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from nba_bingo_grid import Axis, Category
from nba_api_loader import load_dataset_from_api


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_game_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_game_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _rebuild_cell_category(cell: dict, cat_lookup: dict[str, Category]) -> Optional[Category]:
    """Map a game.json cell dict back to its live Category (with predicate)."""
    return cat_lookup.get(cell["id"])


# ─────────────────────────────────────────────────────────────────────────────
# Core audit logic
# ─────────────────────────────────────────────────────────────────────────────

def audit_game_json(
    game_path: str,
    cache_dir: str = "nba_api_cache",
    fix: bool = False,
    player_filter: Optional[str] = None,
) -> int:
    """
    Audit (and optionally fix) all validCellIds in game_path.

    Returns the total number of corrections found.
    """
    if not os.path.exists(game_path):
        print(f"ERROR: game file not found: {game_path}", file=sys.stderr)
        return 0

    print(f"Loading game.json: {game_path}")
    game_data = _load_game_json(game_path)
    games: list[dict] = game_data.get("games", [])
    if not games:
        print("No games found in the file.")
        return 0

    # ── Build full NBA API dataset ───────────────────────────────────────────
    # Use min_games=1 so that every player who ever appears in a game can be
    # looked up, even if they wouldn't normally pass the default threshold.
    print("\nBuilding category/player dataset from NBA API (using cache where fresh)…")
    categories, players = load_dataset_from_api(
        cache_dir=cache_dir, min_games=1
    )

    # Lookups
    cat_lookup: dict[str, Category] = {c.id: c for c in categories}
    player_lookup = {p.id: p for p in players}

    print(f"  {len(categories)} categories, {len(players)} players loaded\n")

    # ── Walk every game ──────────────────────────────────────────────────────
    total_corrections = 0
    total_false_neg = 0
    total_false_pos = 0
    games_with_issues = 0

    for game_idx, game in enumerate(games):
        game_cells: list[dict] = game.get("cells", [])
        sequence: list[dict] = game.get("sequence", [])

        # Map this game's cell ids → live Category objects
        live_cells: list[Optional[Category]] = [
            _rebuild_cell_category(c, cat_lookup) for c in game_cells
        ]
        unmapped = [c["id"] for c, lc in zip(game_cells, live_cells) if lc is None]
        if unmapped:
            print(f"Game {game_idx + 1}: WARNING — {len(unmapped)} cells have no "
                  f"matching category predicate: {unmapped}")

        game_dirty = False

        for entry in sequence:
            player_id = int(entry["id"])
            player_name: str = entry["name"]

            if player_filter and player_filter.lower() not in player_name.lower():
                continue

            stored_valid: list[str] = entry.get("validCellIds", [])
            stored_set = set(stored_valid)

            player = player_lookup.get(player_id)
            if player is None:
                print(f"  Game {game_idx + 1} | {player_name} (id={player_id}): "
                      f"not found in dataset — skipping")
                continue

            # Recompute which cells this player satisfies
            correct_set: set[str] = set()
            for cell_dict, live_cat in zip(game_cells, live_cells):
                if live_cat is not None and live_cat.matches(player):
                    correct_set.add(cell_dict["id"])

            false_negatives = sorted(correct_set - stored_set)
            false_positives = sorted(stored_set - correct_set)

            if false_negatives or false_positives:
                games_with_issues += 1
                total_false_neg += len(false_negatives)
                total_false_pos += len(false_positives)
                total_corrections += len(false_negatives) + len(false_positives)

                print(
                    f"  Game {game_idx + 1} | {player_name} (id={player_id})"
                )
                if false_negatives:
                    # Enrich with human-readable labels
                    labels = [
                        f"{cid} ({cat_lookup[cid].label})"
                        for cid in false_negatives
                        if cid in cat_lookup
                    ]
                    print(f"    FALSE NEGATIVE (+{len(false_negatives)}): {labels}")
                if false_positives:
                    labels = [
                        f"{cid} ({cat_lookup[cid].label})"
                        for cid in false_positives
                        if cid in cat_lookup
                    ]
                    print(f"    FALSE POSITIVE (-{len(false_positives)}): {labels}")

                if fix:
                    # Replace validCellIds with the correct ordered list
                    # (preserve original ordering for cells that remain valid,
                    # then append newly discovered valid cells alphabetically)
                    corrected = [c for c in stored_valid if c in correct_set]
                    corrected += sorted(correct_set - set(corrected))
                    entry["validCellIds"] = corrected
                    game_dirty = True

        if game_dirty:
            print(f"  → Game {game_idx + 1} patched.")

    # ── Summary ─────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    if total_corrections == 0:
        print("✓ No corrections needed — all validCellIds look correct.")
    else:
        print(f"Found {total_corrections} correction(s) across "
              f"{games_with_issues} player-game pair(s):")
        print(f"  False negatives (missing valid cells): {total_false_neg}")
        print(f"  False positives (invalid cells stored): {total_false_pos}")

        if fix:
            _save_game_json(game_path, game_data)
            print(f"\n✓ game.json updated: {game_path}")
        else:
            print(
                "\nRun with --fix to apply corrections automatically.\n"
                "Example:\n"
                f"  python correction_agent.py --game \"{game_path}\" --fix"
            )

    return total_corrections


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit and optionally fix validCellIds in game.json."
    )
    parser.add_argument(
        "--game",
        default="frontend/public/game.json",
        help="Path to game.json (default: frontend/public/game.json)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Rewrite game.json with corrected validCellIds",
    )
    parser.add_argument(
        "--player",
        default=None,
        metavar="NAME",
        help="Only audit entries whose player name contains NAME (case-insensitive)",
    )
    parser.add_argument(
        "--cache-dir",
        default="nba_api_cache",
        help="Directory for NBA API cache files (default: nba_api_cache)",
    )
    args = parser.parse_args()

    corrections = audit_game_json(
        game_path=args.game,
        cache_dir=args.cache_dir,
        fix=args.fix,
        player_filter=args.player,
    )
    sys.exit(0 if corrections == 0 else 1)


if __name__ == "__main__":
    main()
