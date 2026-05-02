"""
Charge le dataset NBA 2024-25 (CSV) et l'assemble en (categories, players)
compatibles avec nba_bingo_grid.py.

Source : NBA_PLAYERS.csv, NBA_TEAMS.csv, NBA_PLAYER_GAMES.csv
- Couvre la régulière + playoffs 2024-25
- 566 joueurs, 30 équipes, ~36k player-games
- TEAM / TEAMMATE / STAT / CAREER / ERA dérivés du CSV
- NATIONALITY / AWARD / DRAFT enrichis manuellement pour ~50 stars
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from typing import Optional

from nba_bingo_grid import Player, Category, Axis


# Enrichissements manuels pour les joueurs notables. Utilise les noms
# EXACTS du CSV (avec diacritiques et suffixes type "III", "Jr.").
ENRICHMENT_BY_NAME: dict[str, dict] = {
    "LeBron James": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA", "ROY"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "Stephen Curry": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA"}),
        "draft_pick": 7, "draft_round": 1, "is_champion": True,
    },
    "Kevin Durant": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA", "ROY"}),
        "draft_pick": 2, "draft_round": 1, "is_champion": True,
    },
    "Giannis Antetokounmpo": {
        "nationality": "GRC",
        "awards": frozenset({"MVP", "Finals MVP", "DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 15, "draft_round": 1, "is_champion": True,
    },
    "Luka Dončić": {
        "nationality": "SVN",
        "awards": frozenset({"All-Star", "All-NBA", "ROY"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": False,
    },
    "Nikola Jokić": {
        "nationality": "SRB",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA"}),
        "draft_pick": 41, "draft_round": 2, "is_champion": True,
    },
    "Joel Embiid": {
        "nationality": "CMR",
        "awards": frozenset({"MVP", "All-Star", "All-NBA"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": False,
    },
    "Jayson Tatum": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": True,
    },
    "Anthony Davis": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA", "DPOY"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "Damian Lillard": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA", "ROY"}),
        "draft_pick": 6, "draft_round": 1, "is_champion": False,
    },
    "Jimmy Butler III": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 30, "draft_round": 1, "is_champion": False,
    },
    "Kawhi Leonard": {
        "nationality": "USA",
        "awards": frozenset({"Finals MVP", "DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 15, "draft_round": 1, "is_champion": True,
    },
    "Paul George": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 10, "draft_round": 1, "is_champion": False,
    },
    "Kyrie Irving": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "James Harden": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "All-Star", "All-NBA", "Sixth Man"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": False,
    },
    "Chris Paul": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA", "ROY"}),
        "draft_pick": 4, "draft_round": 1, "is_champion": False,
    },
    "Klay Thompson": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 11, "draft_round": 1, "is_champion": True,
    },
    "Draymond Green": {
        "nationality": "USA",
        "awards": frozenset({"DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 35, "draft_round": 2, "is_champion": True,
    },
    "Jrue Holiday": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 17, "draft_round": 1, "is_champion": True,
    },
    "Russell Westbrook": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "All-Star", "All-NBA"}),
        "draft_pick": 4, "draft_round": 1, "is_champion": False,
    },
    "Donovan Mitchell": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 13, "draft_round": 1, "is_champion": False,
    },
    "Devin Booker": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 13, "draft_round": 1, "is_champion": False,
    },
    "Karl-Anthony Towns": {
        "nationality": "DOM",
        "awards": frozenset({"All-Star", "All-NBA", "ROY"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Bam Adebayo": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 14, "draft_round": 1, "is_champion": False,
    },
    "Trae Young": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 5, "draft_round": 1, "is_champion": False,
    },
    "Ja Morant": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "ROY"}),
        "draft_pick": 2, "draft_round": 1, "is_champion": False,
    },
    "Zion Williamson": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Shai Gilgeous-Alexander": {
        "nationality": "CAN",
        "awards": frozenset({"MVP", "All-Star", "All-NBA"}),
        "draft_pick": 11, "draft_round": 1, "is_champion": True,
    },
    "Anthony Edwards": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Tyrese Haliburton": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 12, "draft_round": 1, "is_champion": False,
    },
    "Pascal Siakam": {
        "nationality": "CMR",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 27, "draft_round": 1, "is_champion": True,
    },
    "Rudy Gobert": {
        "nationality": "FRA",
        "awards": frozenset({"DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 27, "draft_round": 1, "is_champion": False,
    },
    "Victor Wembanyama": {
        "nationality": "FRA",
        "awards": frozenset({"All-Star", "ROY", "All-NBA", "DPOY"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Cade Cunningham": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Domantas Sabonis": {
        "nationality": "LTU",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 11, "draft_round": 1, "is_champion": False,
    },
    "De'Aaron Fox": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 5, "draft_round": 1, "is_champion": False,
    },
    "Brandon Ingram": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 2, "draft_round": 1, "is_champion": False,
    },
    "Jaren Jackson Jr.": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "DPOY"}),
        "draft_pick": 4, "draft_round": 1, "is_champion": False,
    },
    "Tyrese Maxey": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 21, "draft_round": 1, "is_champion": False,
    },
    "Paolo Banchero": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "ROY"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Lauri Markkanen": {
        "nationality": "FIN",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 7, "draft_round": 1, "is_champion": False,
    },
    "Alperen Sengun": {
        "nationality": "TUR",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 16, "draft_round": 1, "is_champion": False,
    },
    "Franz Wagner": {
        "nationality": "DEU",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 8, "draft_round": 1, "is_champion": False,
    },
    "Jalen Brunson": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 33, "draft_round": 2, "is_champion": False,
    },
    "LaMelo Ball": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "ROY"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": False,
    },
    "Dyson Daniels": {
        "nationality": "AUS",
        "awards": frozenset(),
        "draft_pick": 8, "draft_round": 1, "is_champion": False,
    },
    "Jamal Murray": {
        "nationality": "CAN",
        "awards": frozenset(),
        "draft_pick": 7, "draft_round": 1, "is_champion": True,
    },
    "Andrew Wiggins": {
        "nationality": "CAN",
        "awards": frozenset({"All-Star", "ROY"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "Nikola Vučević": {
        "nationality": "MNE",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 16, "draft_round": 1, "is_champion": False,
    },
    "Bogdan Bogdanović": {
        "nationality": "SRB",
        "awards": frozenset(),
        "draft_pick": 27, "draft_round": 1, "is_champion": False,
    },
    "Bogdan Bogdanovic": {
        "nationality": "SRB",
        "awards": frozenset(),
        "draft_pick": 27, "draft_round": 1, "is_champion": False,
    },
    "Bilal Coulibaly": {
        "nationality": "FRA",
        "awards": frozenset(),
        "draft_pick": 7, "draft_round": 1, "is_champion": False,
    },
    "Evan Fournier": {
        "nationality": "FRA",
        "awards": frozenset(),
        "draft_pick": 20, "draft_round": 1, "is_champion": False,
    },
    "Ivica Zubac": {
        "nationality": "HRV",
        "awards": frozenset(),
        "draft_pick": 32, "draft_round": 2, "is_champion": False,
    },
    "Dario Šarić": {
        "nationality": "HRV",
        "awards": frozenset(),
        "draft_pick": 12, "draft_round": 1, "is_champion": False,
    },
    "Boban Marjanović": {
        "nationality": "SRB",
        "awards": frozenset(),
        "draft_pick": None, "draft_round": None, "is_champion": False,
    },
    "Vasilije Micić": {
        "nationality": "SRB",
        "awards": frozenset(),
        "draft_pick": 52, "draft_round": 2, "is_champion": False,
    },
    "Josh Giddey": {
        "nationality": "AUS",
        "awards": frozenset(),
        "draft_pick": 6, "draft_round": 1, "is_champion": False,
    },
    "Ben Simmons": {
        "nationality": "AUS",
        "awards": frozenset({"All-Star", "All-NBA", "ROY"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Patty Mills": {
        "nationality": "AUS",
        "awards": frozenset(),
        "draft_pick": 55, "draft_round": 2, "is_champion": True,
    },
    "Joel Embiid": {  # already, but kept for safety
        "nationality": "CMR",
        "awards": frozenset({"MVP", "All-Star", "All-NBA"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": False,
    },
    "Lu Dort": {
        "nationality": "CAN",
        "awards": frozenset(),
        "draft_pick": None, "draft_round": None, "is_champion": True,
    },
    "RJ Barrett": {
        "nationality": "CAN",
        "awards": frozenset(),
        "draft_pick": 3, "draft_round": 1, "is_champion": False,
    },
    "Dillon Brooks": {
        "nationality": "CAN",
        "awards": frozenset(),
        "draft_pick": 45, "draft_round": 2, "is_champion": False,
    },
    "Kelly Olynyk": {
        "nationality": "CAN",
        "awards": frozenset(),
        "draft_pick": 13, "draft_round": 1, "is_champion": False,
    },
    "Karl-Anthony Towns": {  # already; left for safety
        "nationality": "DOM",
        "awards": frozenset({"All-Star", "All-NBA", "ROY"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Al Horford": {
        "nationality": "DOM",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": True,
    },
    "Goran Dragić": {
        "nationality": "SVN",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 45, "draft_round": 2, "is_champion": False,
    },
    "Vlatko Čančar": {
        "nationality": "SVN",
        "awards": frozenset(),
        "draft_pick": 49, "draft_round": 2, "is_champion": True,
    },
    "Jonas Valančiūnas": {
        "nationality": "LTU",
        "awards": frozenset(),
        "draft_pick": 5, "draft_round": 1, "is_champion": False,
    },
    "Stephen Curry": {  # safety duplicate
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA"}),
        "draft_pick": 7, "draft_round": 1, "is_champion": True,
    },
}


# Cibles "TEAMMATE" : stars connues qu'on utilise comme repère.
TEAMMATE_TARGETS = [
    "LeBron James", "Stephen Curry", "Nikola Jokić",
    "Giannis Antetokounmpo", "Luka Dončić", "Jayson Tatum",
    "Joel Embiid", "Shai Gilgeous-Alexander", "Kevin Durant",
    "Anthony Edwards",
]


# Équipes "big market" pour le filtre anti-redondance dans nba_bingo_grid.py
# (mêmes IDs que l'ancien jeu, mais ici par abréviation).
POPULAR_TEAMS = {"LAL", "GSW", "BOS", "NYK", "CHI", "MIA"}
BIG_MARKET = {"DEN", "DAL", "PHX", "PHI", "MIL"}


# Mapping nationalité → label affiché côté frontend
NAT_LABELS = {
    "USA": "USA", "FRA": "France", "CAN": "Canada",
    "SRB": "Serbie", "GRC": "Grèce", "ESP": "Espagne",
    "SVN": "Slovénie", "DEU": "Allemagne", "CMR": "Cameroun",
    "DOM": "Rép. Dominicaine", "TUR": "Turquie",
    "FIN": "Finlande", "LTU": "Lituanie", "AUS": "Australie",
    "MNE": "Monténégro", "HRV": "Croatie",
}


# Difficulté par nationalité (USA = très facile, étranger rare = très dur)
NAT_DIFFICULTY = {
    "USA": 1, "FRA": 3, "CAN": 3, "ESP": 3,
    "GRC": 4, "SRB": 4, "CMR": 4, "DEU": 4, "AUS": 4,
    "SVN": 5, "DOM": 5, "TUR": 5, "FIN": 5, "LTU": 5,
    "MNE": 5, "HRV": 5,
}


def _read_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _safe_float(v) -> float:
    try:
        return float(v) if v not in ("", None) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _aggregate_player_games(rows: list[dict]) -> dict[int, dict]:
    """Pour chaque joueur, agrège ses team_seasons et stats moyennes."""
    stats: dict[int, dict] = defaultdict(lambda: {
        "team_seasons": set(),
        "teams": set(),
        "games": 0,
        "min_total": 0.0,
        "pts_total": 0.0,
        "reb_total": 0.0,
        "ast_total": 0.0,
        "seasons": set(),
    })
    for row in rows:
        try:
            pid = int(row["Player_ID"])
            season_id = row["SEASON_ID"]
            year = int(season_id[-4:])
            team_abbr = row["MATCHUP"].split(" ")[0]
        except (ValueError, KeyError):
            continue
        s = stats[pid]
        s["team_seasons"].add((team_abbr, year))
        s["teams"].add(team_abbr)
        s["games"] += 1
        s["min_total"] += _safe_float(row.get("MIN"))
        s["pts_total"] += _safe_float(row.get("PTS"))
        s["reb_total"] += _safe_float(row.get("REB"))
        s["ast_total"] += _safe_float(row.get("AST"))
        s["seasons"].add(year)
    return stats


def load_real_dataset(
    csv_dir: str,
    min_games: int = 15,
) -> tuple[list[Category], list[Player]]:
    """
    Charge le dataset NBA et produit (categories, players).

    `min_games` filtre les joueurs sous-utilisés pour éviter le bruit
    (rookies en garbage time, two-way players obscurs, etc.).
    """
    teams_csv = _read_csv(os.path.join(csv_dir, "NBA_TEAMS.csv"))
    players_csv = _read_csv(os.path.join(csv_dir, "NBA_PLAYERS.csv"))
    games_csv = _read_csv(os.path.join(csv_dir, "NBA_PLAYER_GAMES.csv"))

    # Mapping abréviation → nickname pour le label de cellule
    nick_by_abbr = {row["abbreviation"]: row["nickname"] for row in teams_csv}

    # Mapping id → nom pour les players
    name_by_id = {int(row["id"]): row["full_name"] for row in players_csv}

    aggregated = _aggregate_player_games(games_csv)

    players: list[Player] = []
    for pid, s in aggregated.items():
        if s["games"] < min_games:
            continue
        if pid not in name_by_id:
            continue
        name = name_by_id[pid]
        ppg = s["pts_total"] / s["games"]
        rpg = s["reb_total"] / s["games"]
        apg = s["ast_total"] / s["games"]
        enrich = ENRICHMENT_BY_NAME.get(name, {})
        players.append(Player(
            id=pid,
            name=name,
            teams=frozenset(s["teams"]),
            nationality=enrich.get("nationality", ""),
            awards=enrich.get("awards", frozenset()),
            draft_pick=enrich.get("draft_pick"),
            draft_round=enrich.get("draft_round"),
            career_ppg=ppg,
            career_rpg=rpg,
            career_apg=apg,
            seasons=frozenset(s["seasons"]),
            is_champion=enrich.get("is_champion", False),
            team_seasons=frozenset(s["team_seasons"]),
        ))

    categories = _build_categories(players, nick_by_abbr)
    return categories, players


def _build_categories(
    players: list[Player],
    nick_by_abbr: dict[str, str],
) -> list[Category]:
    cats: list[Category] = []

    # ─── TEAM ───
    abbrs_in_data = {t for p in players for t in p.teams}
    for abbr in sorted(abbrs_in_data):
        nickname = nick_by_abbr.get(abbr, abbr)
        if abbr in POPULAR_TEAMS:
            diff = 1
        elif abbr in BIG_MARKET:
            diff = 2
        else:
            diff = 3
        cats.append(Category(
            id=f"team_{abbr.lower()}",
            label=nickname,
            axis=Axis.TEAM,
            difficulty=diff,
            predicate=lambda p, a=abbr: a in p.teams,
        ))

    # ─── NATIONALITY ───
    nats_present = {p.nationality for p in players if p.nationality}
    for nat in sorted(nats_present):
        if nat not in NAT_LABELS:
            continue
        cats.append(Category(
            id=f"nat_{nat.lower()}",
            label=NAT_LABELS[nat],
            axis=Axis.NATIONALITY,
            difficulty=NAT_DIFFICULTY.get(nat, 4),
            predicate=lambda p, n=nat: p.nationality == n,
        ))

    # ─── AWARD ───
    awards = [
        ("award_mvp", "MVP", 2, "MVP"),
        ("award_finals_mvp", "Finals MVP", 3, "Finals MVP"),
        ("award_dpoy", "DPOY", 3, "DPOY"),
        ("award_roy", "Rookie of the Year", 3, "ROY"),
        ("award_6moy", "Sixth Man", 4, "Sixth Man"),
        ("award_all_star", "All-Star", 1, "All-Star"),
        ("award_all_nba", "All-NBA", 2, "All-NBA"),
    ]
    for cid, label, diff, key in awards:
        cats.append(Category(
            id=cid, label=label, axis=Axis.AWARD, difficulty=diff,
            predicate=lambda p, k=key: k in p.awards,
        ))

    # ─── DRAFT ───
    # On ne peut pas marquer "undrafted" pour les joueurs non enrichis
    # (draft_pick=None signifie "inconnu", pas "non-drafté"), donc on
    # se limite aux catégories où la métadonnée est positive.
    cats.extend([
        Category("draft_pick_1", "1er choix de draft", Axis.DRAFT, 3,
                 lambda p: p.draft_pick == 1),
        Category("draft_top_3", "Top 3 draft", Axis.DRAFT, 2,
                 lambda p: p.draft_pick is not None and p.draft_pick <= 3),
        Category("draft_round_2", "Second tour", Axis.DRAFT, 4,
                 lambda p: p.draft_round == 2),
    ])

    # ─── STAT (basé sur stats 2024-25 du CSV) ───
    cats.extend([
        Category("stat_25_ppg", "25+ PPG en 2024-25", Axis.STAT, 3,
                 lambda p: p.career_ppg >= 25.0),
        Category("stat_30_ppg", "30+ PPG en 2024-25", Axis.STAT, 5,
                 lambda p: p.career_ppg >= 30.0),
        Category("stat_10_rpg", "10+ RPG en 2024-25", Axis.STAT, 4,
                 lambda p: p.career_rpg >= 10.0),
        Category("stat_8_apg", "8+ APG en 2024-25", Axis.STAT, 4,
                 lambda p: p.career_apg >= 8.0),
    ])

    # ─── CAREER ───
    cats.extend([
        Category("career_champion", "Champion NBA", Axis.CAREER, 2,
                 lambda p: p.is_champion),
        Category("career_one_team", "Une seule équipe en 2024-25",
                 Axis.CAREER, 1,
                 lambda p: len(p.teams) == 1),
        Category("career_multi", "A changé d'équipe en 2024-25",
                 Axis.CAREER, 3,
                 lambda p: len(p.teams) >= 2),
    ])

    # ─── ERA ───
    # Tout le monde est actif dans les années 2020 ici, donc D1 trivial.
    cats.append(Category("era_2020s", "Actif dans les années 2020",
                         Axis.ERA, 1,
                         lambda p: any(s >= 2020 for s in p.seasons)))

    # ─── TEAMMATE ───
    by_name = {p.name: p for p in players}
    for star_name in TEAMMATE_TARGETS:
        if star_name not in by_name:
            continue
        target = by_name[star_name]
        if not target.team_seasons:
            continue
        cats.append(Category(
            id=f"teammate_{target.id}",
            label=f"A joué avec {star_name}",
            axis=Axis.TEAMMATE,
            difficulty=3,
            predicate=lambda p, t=target.team_seasons, tid=target.id:
                p.id != tid and bool(p.team_seasons & t),
        ))

    return cats


if __name__ == "__main__":
    csv_dir = "nba_dataset_extracted"
    cats, players = load_real_dataset(csv_dir)
    print(f"Joueurs : {len(players)}")
    print(f"Catégories : {len(cats)}")
    from collections import Counter
    by_axis = Counter(c.axis.value for c in cats)
    print(f"Par axe : {dict(by_axis)}")
