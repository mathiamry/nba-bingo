"""
Load the NBA dataset from the official NBA API and assemble it as
(categories, players) compatible with nba_bingo_grid.py.

Data sources (all via nba_api):
- nba_api.stats.static.players  — full player roster with IDs and active status
- PlayerCareerStats              — per-season, per-team career totals (RS only)
- CommonPlayerInfo               — draft year/round/number, birth country

Awards, nationality and championship flags are still sourced from
ENRICHMENT_BY_NAME (see nba_dataset_loader.py) because those are not
available in structured form from the NBA stats API.

Local cache: nba_api_cache/<player_id>.json
  - active players:  refreshed after ACTIVE_REFRESH_DAYS  (default 7)
  - retired players: refreshed after RETIRED_REFRESH_DAYS (default 30)
  - force_refresh=True ignores cache entirely
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

from nba_api.stats.static import players as static_players
from nba_api.stats.static import teams as static_teams
from nba_api.stats.endpoints import PlayerCareerStats, CommonPlayerInfo

from nba_bingo_grid import Player, Category, Axis
from nba_dataset_loader import (
    ENRICHMENT_BY_NAME,
    HISTORICAL_TEAM_NAMES,
    _build_categories,
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

ACTIVE_REFRESH_DAYS = 7
RETIRED_REFRESH_DAYS = 30
API_DELAY = 0.65          # seconds between consecutive NBA API requests
RECENT_SEASON_CUTOFF = 2024  # year >= this is considered "recent" (2024-25 or later)


# ─────────────────────────────────────────────────────────────────────────────
# Team nickname lookup (current + historical)
# ─────────────────────────────────────────────────────────────────────────────

def _build_nick_by_abbr() -> dict[str, str]:
    nick: dict[str, str] = {}
    for t in static_teams.get_teams():
        nick[t["abbreviation"]] = t["nickname"]
    nick.update(HISTORICAL_TEAM_NAMES)
    return nick


# ─────────────────────────────────────────────────────────────────────────────
# Cache helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cache_path(cache_dir: str, player_id: int) -> str:
    return os.path.join(cache_dir, f"{player_id}.json")


def _cache_is_fresh(path: str, max_age_days: int) -> bool:
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        fetched = data.get("_fetched_at")
        if not fetched:
            return False
        age_days = (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(fetched)
        ).days
        return age_days < max_age_days
    except (json.JSONDecodeError, ValueError, OSError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# NBA API fetch — one player at a time
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_player_data(player_id: int, is_active: bool) -> dict:
    """Query the NBA API for one player's career stats and bio."""
    # ── Career stats per season ──────────────────────────────────────────────
    time.sleep(API_DELAY)
    cs = PlayerCareerStats(player_id=player_id, per_mode36="Totals", timeout=30)
    df = cs.season_totals_regular_season.get_data_frame()

    seasons: list[dict] = []
    for _, row in df.iterrows():
        team_abbr = str(row.get("TEAM_ABBREVIATION") or "")
        # Skip aggregate "TOT" rows (mid-season trade totals) — not a real team.
        if not team_abbr or team_abbr == "TOT":
            continue
        season_id = str(row.get("SEASON_ID") or "")
        # Season format: "2024-25" → ending year = 2025
        try:
            year = int(season_id[:4]) + 1
        except (ValueError, TypeError):
            continue
        seasons.append({
            "season_id": season_id,
            "year": year,
            "team": team_abbr,
            "gp": int(row.get("GP") or 0),
            "pts": float(row.get("PTS") or 0),
            "reb": float(row.get("REB") or 0),
            "ast": float(row.get("AST") or 0),
        })

    # ── Player bio (draft info, country) ────────────────────────────────────
    time.sleep(API_DELAY)
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None
    country: str = ""
    try:
        info = CommonPlayerInfo(player_id=player_id, timeout=30)
        ci = info.common_player_info.get_data_frame()
        if len(ci) > 0:
            row = ci.iloc[0]
            dr_raw = str(row.get("DRAFT_ROUND") or "Undrafted")
            dn_raw = str(row.get("DRAFT_NUMBER") or "Undrafted")
            draft_round = (
                None if dr_raw in ("Undrafted", "", "None", "0")
                else int(dr_raw)
            )
            draft_pick = (
                None if dn_raw in ("Undrafted", "", "None", "0")
                else int(dn_raw)
            )
            country = str(row.get("COUNTRY") or "")
    except Exception:
        pass

    return {
        "_fetched_at": datetime.now(timezone.utc).isoformat(),
        "is_active": is_active,
        "seasons": seasons,
        "draft_round": draft_round,
        "draft_pick": draft_pick,
        "country": country,
    }


def _load_or_fetch(
    player_id: int,
    is_active: bool,
    cache_dir: str,
    force_refresh: bool,
) -> tuple[dict, bool]:
    """Return (player_data, from_cache)."""
    path = _cache_path(cache_dir, player_id)
    max_age = ACTIVE_REFRESH_DAYS if is_active else RETIRED_REFRESH_DAYS
    if not force_refresh and _cache_is_fresh(path, max_age):
        with open(path, encoding="utf-8") as f:
            return json.load(f), True
    data = _fetch_player_data(player_id, is_active)
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data, False


# ─────────────────────────────────────────────────────────────────────────────
# Player object construction
# ─────────────────────────────────────────────────────────────────────────────

def _build_player(player_id: int, full_name: str, data: dict) -> Optional[Player]:
    """Build a Player dataclass from cached API data + manual enrichment."""
    seasons_raw = data.get("seasons", [])

    team_seasons: set[tuple[str, int]] = set()
    teams: set[str] = set()
    season_years: set[int] = set()
    total_games = 0
    pts_total = reb_total = ast_total = 0.0

    for s in seasons_raw:
        gp = s.get("gp", 0)
        if gp == 0:
            continue
        team = s["team"]
        year = s["year"]
        team_seasons.add((team, year))
        teams.add(team)
        season_years.add(year)
        total_games += gp
        pts_total += s.get("pts", 0.0)
        reb_total += s.get("reb", 0.0)
        ast_total += s.get("ast", 0.0)

    if total_games == 0:
        return None

    career_ppg = pts_total / total_games
    career_rpg = reb_total / total_games
    career_apg = ast_total / total_games

    enrich = ENRICHMENT_BY_NAME.get(full_name, {})

    # Draft info: manual enrichment takes priority; API fills missing gaps.
    draft_pick = enrich.get("draft_pick", data.get("draft_pick"))
    draft_round = enrich.get("draft_round", data.get("draft_round"))

    return Player(
        id=player_id,
        name=full_name,
        teams=frozenset(teams),
        nationality=enrich.get("nationality", ""),
        awards=enrich.get("awards", frozenset()),
        draft_pick=draft_pick,
        draft_round=draft_round,
        career_ppg=career_ppg,
        career_rpg=career_rpg,
        career_apg=career_apg,
        seasons=frozenset(season_years),
        is_champion=enrich.get("is_champion", False),
        team_seasons=frozenset(team_seasons),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def load_dataset_from_api(
    cache_dir: str = "nba_api_cache",
    min_games: int = 15,
    force_refresh: bool = False,
) -> tuple[list[Category], list[Player]]:
    """
    Build (categories, players) from the NBA API with local caching.

    cache_dir     : directory for per-player JSON cache files
    min_games     : minimum recent-season games to include an active player
    force_refresh : ignore cache timestamps and re-fetch all players
    """
    all_nba_players = static_players.get_players()
    total = len(all_nba_players)
    print(f"NBA API roster: {total} players total")

    nick_by_abbr = _build_nick_by_abbr()

    players: list[Player] = []
    fetched_count = cache_hit_count = error_count = 0

    for i, p_info in enumerate(all_nba_players):
        player_id = int(p_info["id"])
        full_name = str(p_info["full_name"])
        is_active = bool(p_info.get("is_active", False))

        try:
            data, from_cache = _load_or_fetch(
                player_id, is_active, cache_dir, force_refresh
            )
        except Exception as exc:
            error_count += 1
            print(f"  ⚠  [{i + 1}/{total}] {full_name}: {exc}")
            continue

        if from_cache:
            cache_hit_count += 1
        else:
            fetched_count += 1
            if fetched_count % 100 == 0:
                print(f"  … fetched {fetched_count} players from API so far")

        player = _build_player(player_id, full_name, data)
        if player is None:
            continue

        # Only include players from the modern era (post-1996).
        if not player.seasons or max(player.seasons) < 1996:
            continue

        # Inclusion threshold: active enough recently OR substantial career.
        seasons_raw = data.get("seasons", [])
        career_games = sum(s["gp"] for s in seasons_raw)
        recent_games = sum(
            s["gp"] for s in seasons_raw if s["year"] >= RECENT_SEASON_CUTOFF
        )

        if recent_games >= min_games or career_games >= 150:
            players.append(player)

    print(
        f"Cache hits: {cache_hit_count} | API fetches: {fetched_count} | "
        f"Errors: {error_count}"
    )
    print(f"Players after filtering: {len(players)}")

    categories = _build_categories(players, nick_by_abbr)
    return categories, players


# ─────────────────────────────────────────────────────────────────────────────
# CLI: warm-up / refresh the cache
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Warm up or refresh the NBA API player cache."
    )
    parser.add_argument(
        "--cache-dir", default="nba_api_cache",
        help="Directory for JSON cache files (default: nba_api_cache)"
    )
    parser.add_argument(
        "--refresh", action="store_true",
        help="Force re-fetch of all players, ignoring cached data"
    )
    parser.add_argument(
        "--min-games", type=int, default=15,
        help="Minimum recent-season games to include active players (default: 15)"
    )
    args = parser.parse_args()

    cats, players = load_dataset_from_api(
        cache_dir=args.cache_dir,
        min_games=args.min_games,
        force_refresh=args.refresh,
    )
    print(f"\nCategories : {len(cats)}")
    print(f"Players    : {len(players)}")

    from collections import Counter
    by_axis = Counter(c.axis.value for c in cats)
    print(f"By axis    : {dict(by_axis)}")

    enriched = sum(1 for p in players if p.nationality or p.awards)
    print(f"Enriched   : {enriched}")
