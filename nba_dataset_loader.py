"""
Charge le dataset NBA (CSV) et l'assemble en (categories, players)
compatibles avec nba_bingo_grid.py.

Sources :
- nba_dataset_extracted/NBA_PLAYERS.csv      — catalogue global des joueurs
- nba_dataset_extracted/NBA_PLAYER_GAMES.csv — logs de matches 2024-25
- player_stats_traditionnal_rs.csv           — stats saisonnières 1996-2023

Les deux fichiers de stats sont fusionnés : un joueur peut provenir du
seul dataset historique (Kobe, Jordan, Duncan…) ou des deux (LeBron).
Les catégories stat reflètent les moyennes de carrière pondérées par
les matchs joués. Les équipes et team_seasons couvrent toute la carrière
disponible dans les deux fichiers.
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from typing import Optional

from nba_bingo_grid import Player, Category, Axis


# ─────────────────────────────────────────────────────────────────────────────
# Enrichissements manuels — nationality, awards, draft, champion, olympique.
# Utilise les noms EXACTS tels qu'ils figurent dans NBA_PLAYERS.csv.
# ─────────────────────────────────────────────────────────────────────────────
ENRICHMENT_BY_NAME: dict[str, dict] = {

    # ── Superstars actifs ────────────────────────────────────────────────────

    "LeBron James": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA", "ROY",
                             "Olympic Gold 2024"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "Stephen Curry": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA",
                             "Olympic Gold 2024"}),
        "draft_pick": 7, "draft_round": 1, "is_champion": True,
    },
    "Kevin Durant": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA", "ROY",
                             "Olympic Gold 2024"}),
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
        "awards": frozenset({"MVP", "All-Star", "All-NBA", "Olympic Gold 2024"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": False,
    },
    "Jayson Tatum": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA", "Olympic Gold 2024"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": True,
    },
    "Anthony Davis": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA", "DPOY", "Olympic Gold 2024"}),
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
        "awards": frozenset({"All-Star", "All-NBA", "Olympic Gold 2024"}),
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
        "awards": frozenset({"All-Star", "All-NBA", "Olympic Gold 2024"}),
        "draft_pick": 13, "draft_round": 1, "is_champion": False,
    },
    "Karl-Anthony Towns": {
        "nationality": "DOM",
        "awards": frozenset({"All-Star", "All-NBA", "ROY"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Bam Adebayo": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA", "Olympic Gold 2024"}),
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
        "awards": frozenset({"All-Star", "All-NBA", "Olympic Gold 2024"}),
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
        "awards": frozenset({"DPOY", "All-Star", "All-NBA", "Olympic Silver 2024"}),
        "draft_pick": 27, "draft_round": 1, "is_champion": False,
    },
    "Victor Wembanyama": {
        "nationality": "FRA",
        "awards": frozenset({"ROY", "DPOY", "All-Star", "All-NBA",
                             "Olympic Silver 2024"}),
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
        "awards": frozenset({"Olympic Silver 2024"}),
        "draft_pick": 7, "draft_round": 1, "is_champion": False,
    },
    "Evan Fournier": {
        "nationality": "FRA",
        "awards": frozenset({"Olympic Silver 2024"}),
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

    # ── Récents / semi-récents USA ──────────────────────────────────────────

    "Aaron Gordon": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 4, "draft_round": 1, "is_champion": True,
    },
    "Alex Caruso": {
        "nationality": "USA",
        "awards": frozenset({"Olympic Gold 2024"}),
        "draft_pick": None, "draft_round": None, "is_champion": True,
    },
    "Anfernee Simons": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 24, "draft_round": 1, "is_champion": False,
    },
    "Bobby Portis": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 22, "draft_round": 1, "is_champion": True,
    },
    "Bradley Beal": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": False,
    },
    "Brook Lopez": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 10, "draft_round": 1, "is_champion": True,
    },
    "Chet Holmgren": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 2, "draft_round": 1, "is_champion": True,
    },
    "CJ McCollum": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 10, "draft_round": 1, "is_champion": False,
    },
    "DeMar DeRozan": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 9, "draft_round": 1, "is_champion": False,
    },
    "Derrick White": {
        "nationality": "USA",
        "awards": frozenset({"Olympic Gold 2024"}),
        "draft_pick": 29, "draft_round": 1, "is_champion": True,
    },
    "Evan Mobley": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 3, "draft_round": 1, "is_champion": False,
    },
    "Fred VanVleet": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": None, "draft_round": None, "is_champion": True,
    },
    "Gordon Hayward": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 9, "draft_round": 1, "is_champion": False,
    },
    "Grayson Allen": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 21, "draft_round": 1, "is_champion": True,
    },
    "Isaiah Thomas": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 60, "draft_round": 2, "is_champion": False,
    },
    "Jaden Ivey": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 5, "draft_round": 1, "is_champion": False,
    },
    "Jalen Williams": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 12, "draft_round": 1, "is_champion": True,
    },
    "James Wiseman": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 2, "draft_round": 1, "is_champion": True,
    },
    "Jarrett Allen": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 22, "draft_round": 1, "is_champion": False,
    },
    "Jaylen Brown": {
        "nationality": "USA",
        "awards": frozenset({"Finals MVP", "All-Star", "All-NBA"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": True,
    },
    "John Wall": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Jordan Clarkson": {
        "nationality": "USA",
        "awards": frozenset({"Sixth Man"}),
        "draft_pick": 46, "draft_round": 2, "is_champion": False,
    },
    "Jordan Nwora": {
        "nationality": "NGA",
        "awards": frozenset(),
        "draft_pick": 45, "draft_round": 2, "is_champion": True,
    },
    "Jordan Poole": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 28, "draft_round": 1, "is_champion": True,
    },
    "Julius Randle": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 7, "draft_round": 1, "is_champion": False,
    },
    "Keegan Murray": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 4, "draft_round": 1, "is_champion": False,
    },
    "Keldon Johnson": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 29, "draft_round": 1, "is_champion": False,
    },
    "Kemba Walker": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 9, "draft_round": 1, "is_champion": False,
    },
    "Kentavious Caldwell-Pope": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 8, "draft_round": 1, "is_champion": True,
    },
    "Kevin Love": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 5, "draft_round": 1, "is_champion": True,
    },
    "Khris Middleton": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 39, "draft_round": 2, "is_champion": True,
    },
    "Kyle Kuzma": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 27, "draft_round": 1, "is_champion": True,
    },
    "Kyle Lowry": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 24, "draft_round": 1, "is_champion": True,
    },
    "Lonzo Ball": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 2, "draft_round": 1, "is_champion": False,
    },
    "Lou Williams": {
        "nationality": "USA",
        "awards": frozenset({"Sixth Man"}),
        "draft_pick": 45, "draft_round": 2, "is_champion": False,
    },
    "Marcus Smart": {
        "nationality": "USA",
        "awards": frozenset({"DPOY"}),
        "draft_pick": 6, "draft_round": 1, "is_champion": False,
    },
    "Michael Carter-Williams": {
        "nationality": "USA",
        "awards": frozenset({"ROY"}),
        "draft_pick": 11, "draft_round": 1, "is_champion": False,
    },
    "Michael Porter Jr.": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 14, "draft_round": 1, "is_champion": True,
    },
    "Mikal Bridges": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 10, "draft_round": 1, "is_champion": False,
    },
    "Miles Bridges": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 12, "draft_round": 1, "is_champion": False,
    },
    "Montrezl Harrell": {
        "nationality": "USA",
        "awards": frozenset({"Sixth Man"}),
        "draft_pick": 32, "draft_round": 2, "is_champion": False,
    },
    "Norman Powell": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 46, "draft_round": 2, "is_champion": True,
    },
    "OG Anunoby": {
        "nationality": "GBR",
        "awards": frozenset(),
        "draft_pick": 23, "draft_round": 1, "is_champion": True,
    },
    "P.J. Tucker": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": None, "draft_round": None, "is_champion": True,
    },
    "Scottie Barnes": {
        "nationality": "CAN",
        "awards": frozenset({"ROY"}),
        "draft_pick": 4, "draft_round": 1, "is_champion": False,
    },
    "Terry Rozier": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 16, "draft_round": 1, "is_champion": False,
    },
    "Tobias Harris": {
        "nationality": "USA",
        "awards": frozenset(),
        "draft_pick": 19, "draft_round": 1, "is_champion": False,
    },
    "Zach LaVine": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 13, "draft_round": 1, "is_champion": False,
    },

    # ── Internationaux récents ───────────────────────────────────────────────

    "Anderson Varejao": {
        "nationality": "BRA",
        "awards": frozenset(),
        "draft_pick": 30, "draft_round": 1, "is_champion": False,
    },
    "Andrew Bogut": {
        "nationality": "AUS",
        "awards": frozenset(),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "Bismack Biyombo": {
        "nationality": "COD",
        "awards": frozenset(),
        "draft_pick": 7, "draft_round": 1, "is_champion": False,
    },
    "Bol Bol": {
        "nationality": "SDN",
        "awards": frozenset(),
        "draft_pick": 44, "draft_round": 2, "is_champion": False,
    },
    "Boris Diaw": {
        "nationality": "FRA",
        "awards": frozenset(),
        "draft_pick": 21, "draft_round": 1, "is_champion": True,
    },
    "Buddy Hield": {
        "nationality": "BAH",
        "awards": frozenset(),
        "draft_pick": 6, "draft_round": 1, "is_champion": False,
    },
    "Clint Capela": {
        "nationality": "CHE",
        "awards": frozenset(),
        "draft_pick": 25, "draft_round": 1, "is_champion": False,
    },
    "Danilo Gallinari": {
        "nationality": "ITA",
        "awards": frozenset(),
        "draft_pick": 6, "draft_round": 1, "is_champion": False,
    },
    "Davis Bertans": {
        "nationality": "LVA",
        "awards": frozenset(),
        "draft_pick": 42, "draft_round": 2, "is_champion": False,
    },
    "Dennis Schröder": {
        "nationality": "DEU",
        "awards": frozenset(),
        "draft_pick": 17, "draft_round": 1, "is_champion": False,
    },
    "Facundo Campazzo": {
        "nationality": "ARG",
        "awards": frozenset(),
        "draft_pick": 45, "draft_round": 2, "is_champion": False,
    },
    "Frank Ntilikina": {
        "nationality": "FRA",
        "awards": frozenset({"Olympic Silver 2024"}),
        "draft_pick": 8, "draft_round": 1, "is_champion": False,
    },
    "Goga Bitadze": {
        "nationality": "GEO",
        "awards": frozenset(),
        "draft_pick": 18, "draft_round": 1, "is_champion": False,
    },
    "Joe Ingles": {
        "nationality": "AUS",
        "awards": frozenset(),
        "draft_pick": 31, "draft_round": 2, "is_champion": False,
    },
    "Killian Hayes": {
        "nationality": "FRA",
        "awards": frozenset(),
        "draft_pick": 7, "draft_round": 1, "is_champion": False,
    },
    "Kristaps Porzingis": {
        "nationality": "LVA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 4, "draft_round": 1, "is_champion": True,
    },
    "Leandro Barbosa": {
        "nationality": "BRA",
        "awards": frozenset({"Sixth Man"}),
        "draft_pick": 28, "draft_round": 1, "is_champion": False,
    },
    "Luc Mbah a Moute": {
        "nationality": "CMR",
        "awards": frozenset(),
        "draft_pick": 37, "draft_round": 2, "is_champion": False,
    },
    "Luis Scola": {
        "nationality": "ARG",
        "awards": frozenset(),
        "draft_pick": 56, "draft_round": 2, "is_champion": False,
    },
    "Marco Belinelli": {
        "nationality": "ITA",
        "awards": frozenset(),
        "draft_pick": 18, "draft_round": 1, "is_champion": True,
    },
    "Matthew Dellavedova": {
        "nationality": "AUS",
        "awards": frozenset(),
        "draft_pick": 44, "draft_round": 2, "is_champion": True,
    },
    "Naz Reid": {
        "nationality": "CAN",
        "awards": frozenset({"Sixth Man"}),
        "draft_pick": 58, "draft_round": 2, "is_champion": False,
    },
    "Nene": {
        "nationality": "BRA",
        "awards": frozenset(),
        "draft_pick": 7, "draft_round": 1, "is_champion": False,
    },
    "Nicolas Batum": {
        "nationality": "FRA",
        "awards": frozenset({"Olympic Silver 2024"}),
        "draft_pick": 25, "draft_round": 1, "is_champion": False,
    },
    "Nikola Mirotic": {
        "nationality": "MNE",
        "awards": frozenset(),
        "draft_pick": 23, "draft_round": 1, "is_champion": False,
    },
    "Ricky Rubio": {
        "nationality": "ESP",
        "awards": frozenset(),
        "draft_pick": 5, "draft_round": 1, "is_champion": False,
    },
    "Santi Aldama": {
        "nationality": "ESP",
        "awards": frozenset(),
        "draft_pick": 30, "draft_round": 1, "is_champion": False,
    },
    "Serge Ibaka": {
        "nationality": "COG",
        "awards": frozenset(),
        "draft_pick": 24, "draft_round": 1, "is_champion": True,
    },
    "Steven Adams": {
        "nationality": "NZL",
        "awards": frozenset(),
        "draft_pick": 12, "draft_round": 1, "is_champion": False,
    },
    "Thon Maker": {
        "nationality": "SDN",
        "awards": frozenset(),
        "draft_pick": 10, "draft_round": 1, "is_champion": False,
    },

    # ── Légendes historiques USA (1996-2023) ────────────────────────────────

    "Allen Iverson": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "ROY", "All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Alonzo Mourning": {
        "nationality": "USA",
        "awards": frozenset({"DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 2, "draft_round": 1, "is_champion": True,
    },
    "Blake Griffin": {
        "nationality": "USA",
        "awards": frozenset({"ROY", "All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Carmelo Anthony": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": False,
    },
    "Charles Barkley": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "All-Star", "All-NBA"}),
        "draft_pick": 5, "draft_round": 1, "is_champion": False,
    },
    "Chris Bosh": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 4, "draft_round": 1, "is_champion": True,
    },
    "Chris Webber": {
        "nationality": "USA",
        "awards": frozenset({"ROY", "All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "David Robinson": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "Dennis Rodman": {
        "nationality": "USA",
        "awards": frozenset({"DPOY"}),
        "draft_pick": 27, "draft_round": 2, "is_champion": True,
    },
    "Derrick Rose": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "ROY", "All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Dikembe Mutombo": {
        "nationality": "COD",
        "awards": frozenset({"DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 4, "draft_round": 1, "is_champion": False,
    },
    "Dirk Nowitzki": {
        "nationality": "DEU",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA"}),
        "draft_pick": 9, "draft_round": 1, "is_champion": True,
    },
    "Dwight Howard": {
        "nationality": "USA",
        "awards": frozenset({"DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "Dwyane Wade": {
        "nationality": "USA",
        "awards": frozenset({"Finals MVP", "All-Star", "All-NBA"}),
        "draft_pick": 5, "draft_round": 1, "is_champion": True,
    },
    "Gary Payton": {
        "nationality": "USA",
        "awards": frozenset({"DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 2, "draft_round": 1, "is_champion": True,
    },
    "Gilbert Arenas": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 31, "draft_round": 2, "is_champion": False,
    },
    "Hakeem Olajuwon": {
        "nationality": "NGA",
        "awards": frozenset({"MVP", "Finals MVP", "DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "Jason Kidd": {
        "nationality": "USA",
        "awards": frozenset({"ROY", "All-Star", "All-NBA"}),
        "draft_pick": 2, "draft_round": 1, "is_champion": True,
    },
    "John Stockton": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 16, "draft_round": 1, "is_champion": False,
    },
    "Karl Malone": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "All-Star", "All-NBA"}),
        "draft_pick": 13, "draft_round": 1, "is_champion": False,
    },
    "Kevin Garnett": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 5, "draft_round": 1, "is_champion": True,
    },
    "Kobe Bryant": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA"}),
        "draft_pick": 13, "draft_round": 1, "is_champion": True,
    },
    "Manu Ginobili": {
        "nationality": "ARG",
        "awards": frozenset({"All-Star", "Sixth Man"}),
        "draft_pick": 57, "draft_round": 2, "is_champion": True,
    },
    "Marc Gasol": {
        "nationality": "ESP",
        "awards": frozenset({"DPOY", "All-Star", "All-NBA"}),
        "draft_pick": 48, "draft_round": 2, "is_champion": True,
    },
    "Michael Jordan": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "DPOY", "ROY",
                             "All-Star", "All-NBA"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": True,
    },
    "Patrick Ewing": {
        "nationality": "JAM",
        "awards": frozenset({"ROY", "All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": False,
    },
    "Paul Pierce": {
        "nationality": "USA",
        "awards": frozenset({"Finals MVP", "All-Star", "All-NBA"}),
        "draft_pick": 10, "draft_round": 1, "is_champion": True,
    },
    "Pau Gasol": {
        "nationality": "ESP",
        "awards": frozenset({"ROY", "All-Star", "All-NBA"}),
        "draft_pick": 3, "draft_round": 1, "is_champion": True,
    },
    "Rajon Rondo": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 21, "draft_round": 1, "is_champion": True,
    },
    "Ray Allen": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 5, "draft_round": 1, "is_champion": True,
    },
    "Reggie Miller": {
        "nationality": "USA",
        "awards": frozenset({"All-Star"}),
        "draft_pick": 11, "draft_round": 1, "is_champion": False,
    },
    "Scottie Pippen": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 5, "draft_round": 1, "is_champion": True,
    },
    "Shaquille O'Neal": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "ROY", "All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "Steve Nash": {
        "nationality": "CAN",
        "awards": frozenset({"MVP", "All-Star", "All-NBA"}),
        "draft_pick": 15, "draft_round": 1, "is_champion": False,
    },
    "Tim Duncan": {
        "nationality": "USA",
        "awards": frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA"}),
        "draft_pick": 1, "draft_round": 1, "is_champion": True,
    },
    "Tony Parker": {
        "nationality": "FRA",
        "awards": frozenset({"Finals MVP", "All-Star", "All-NBA"}),
        "draft_pick": 28, "draft_round": 1, "is_champion": True,
    },
    "Tracy McGrady": {
        "nationality": "USA",
        "awards": frozenset({"All-Star", "All-NBA"}),
        "draft_pick": 9, "draft_round": 1, "is_champion": False,
    },
    "Vince Carter": {
        "nationality": "USA",
        "awards": frozenset({"ROY", "All-Star", "All-NBA"}),
        "draft_pick": 5, "draft_round": 1, "is_champion": False,
    },
}


# Noms d'équipes historiques absentes de NBA_TEAMS.csv
HISTORICAL_TEAM_NAMES: dict[str, str] = {
    "VAN": "Grizzlies de Vancouver",
    "SEA": "SuperSonics de Seattle",
    "NJN": "Nets du New Jersey",
    "NOH": "Hornets de La Nouvelle-Orléans",
    "NOK": "Hornets de La Nouvelle-Orléans/OKC",
    "CHH": "Hornets de Charlotte",
    "CHA": "Bobcats de Charlotte",
    "WSB": "Bullets de Washington",
}


# Cibles TEAMMATE : stars utilisées comme points de repère.
TEAMMATE_TARGETS = [
    # Actifs / récents
    "LeBron James", "Stephen Curry", "Nikola Jokić",
    "Giannis Antetokounmpo", "Luka Dončić", "Jayson Tatum",
    "Joel Embiid", "Shai Gilgeous-Alexander", "Kevin Durant",
    "Anthony Edwards", "Victor Wembanyama", "Damian Lillard",
    "Jaylen Brown", "LaMelo Ball",
    # Légendes (dans le dataset historique 1996-2023)
    "Kobe Bryant", "Shaquille O'Neal", "Tim Duncan",
    "Michael Jordan", "Dwyane Wade", "Kevin Garnett",
    "Dirk Nowitzki", "Allen Iverson",
]


POPULAR_TEAMS = {"LAL", "GSW", "BOS", "NYK", "CHI", "MIA"}
BIG_MARKET = {"DEN", "DAL", "PHX", "PHI", "MIL"}


NAT_LABELS = {
    "USA": "USA",       "FRA": "France",      "CAN": "Canada",
    "SRB": "Serbie",    "GRC": "Grèce",       "ESP": "Espagne",
    "SVN": "Slovénie",  "DEU": "Allemagne",   "CMR": "Cameroun",
    "DOM": "Rép. Dominicaine", "TUR": "Turquie",
    "FIN": "Finlande",  "LTU": "Lituanie",    "AUS": "Australie",
    "MNE": "Monténégro", "HRV": "Croatie",
    # Nouveaux
    "ARG": "Argentine", "BRA": "Brésil",      "NGA": "Nigeria",
    "LVA": "Lettonie",  "COD": "Rép. Dém. du Congo",
    "COG": "Rép. du Congo", "NZL": "Nouvelle-Zélande",
    "BAH": "Bahamas",   "ITA": "Italie",      "SDN": "Soudan",
    "GEO": "Géorgie",   "CHE": "Suisse",      "GBR": "Grande-Bretagne",
    "JAM": "Jamaïque",
}

NAT_DIFFICULTY = {
    "USA": 1, "FRA": 3, "CAN": 3, "ESP": 3,
    "GRC": 4, "SRB": 4, "CMR": 4, "DEU": 4, "AUS": 4,
    "SVN": 5, "DOM": 5, "TUR": 5, "FIN": 5, "LTU": 5,
    "MNE": 5, "HRV": 5,
    "ARG": 5, "BRA": 5, "NGA": 5, "LVA": 5, "COD": 5,
    "COG": 5, "NZL": 5, "BAH": 5, "ITA": 5, "SDN": 5,
    "GEO": 5, "CHE": 5, "GBR": 5, "JAM": 5,
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers CSV
# ─────────────────────────────────────────────────────────────────────────────

def _read_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _safe_float(v) -> float:
    try:
        return float(v) if v not in ("", None) else 0.0
    except (TypeError, ValueError):
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Agrégation — logs de matchs 2024-25 (une ligne = un match)
# ─────────────────────────────────────────────────────────────────────────────

def _aggregate_player_games(rows: list[dict]) -> dict[int, dict]:
    """Agrège les logs de matchs 2024-25 par joueur."""
    stats: dict[int, dict] = defaultdict(lambda: {
        "team_seasons": set(), "teams": set(), "games": 0,
        "pts_total": 0.0, "reb_total": 0.0, "ast_total": 0.0,
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
        s["pts_total"] += _safe_float(row.get("PTS"))
        s["reb_total"] += _safe_float(row.get("REB"))
        s["ast_total"] += _safe_float(row.get("AST"))
        s["seasons"].add(year)
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Agrégation — stats saisonnières historiques 1996-2023
# (une ligne = un joueur × une saison ; stats déjà en moyennes par match)
# ─────────────────────────────────────────────────────────────────────────────

def _aggregate_historical(rows: list[dict]) -> dict[int, dict]:
    """
    Agrège le fichier player_stats_traditionnal_rs.csv.

    Les stats (PTS, REB, AST) sont des moyennes par match dans ce fichier ;
    on les re-multiplie par GP pour obtenir des totaux pondérables.
    Format SEASON : "1996-97"  →  year = int("1996") + 1 = 1997.
    """
    stats: dict[int, dict] = defaultdict(lambda: {
        "team_seasons": set(), "teams": set(), "games": 0,
        "pts_total": 0.0, "reb_total": 0.0, "ast_total": 0.0,
        "seasons": set(),
    })
    for row in rows:
        try:
            pid = int(row["PLAYER_ID"])
            season = row["SEASON"]              # "1996-97"
            year = int(season[:4]) + 1          # → 1997
            team = row["TEAM_ABBREVIATION"]
            gp = int(float(row["GP"] or 0))
        except (ValueError, KeyError):
            continue
        if gp == 0:
            continue
        s = stats[pid]
        s["team_seasons"].add((team, year))
        s["teams"].add(team)
        s["games"] += gp
        s["pts_total"] += _safe_float(row.get("PTS")) * gp
        s["reb_total"] += _safe_float(row.get("REB")) * gp
        s["ast_total"] += _safe_float(row.get("AST")) * gp
        s["seasons"].add(year)
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Chargement principal
# ─────────────────────────────────────────────────────────────────────────────

# Overrides manuels (équipe, saison) pour patcher les transactions
# récentes que le dataset 2024-25 ne couvre pas. À étendre au fil
# des signatures importantes — l'idéal serait de remplacer le CSV par
# un fetch live via nba_api une fois par mois.
TEAM_SEASONS_OVERRIDES: dict[str, set[tuple[str, int]]] = {
    "Seth Curry": {("GSW", 2025)},
}


def _fame_score(p: Player) -> float:
    """
    Score de notoriété grossier pour ranger les joueurs du plus connu
    au plus obscur. Utilisé pour filtrer le pool aux ~500 joueurs les
    plus reconnaissables, en gardant naturellement quelques pièges
    parmi les role players de bas de tier.
    """
    score = p.career_ppg
    score += len(p.awards) * 5.0
    score += min(len(p.seasons), 12) * 0.5
    if p.is_champion:
        score += 5.0
    return score


def load_real_dataset(
    csv_dir: str,
    hist_csv: Optional[str] = None,
    min_games: int = 15,
    top_n: Optional[int] = 500,
) -> tuple[list[Category], list[Player]]:
    """
    Charge et fusionne les deux sources de données NBA.

    csv_dir   : dossier contenant NBA_PLAYERS.csv, NBA_TEAMS.csv,
                NBA_PLAYER_GAMES.csv.
    hist_csv  : chemin vers player_stats_traditionnal_rs.csv (1996-2023).
                Si None, cherche dans le même dossier que ce module.
    min_games : seuil minimum de matchs en 2024-25 pour les joueurs
                présents uniquement dans le dataset live. Les joueurs
                exclusivement dans le dataset historique doivent avoir
                joué ≥ 150 matchs au total.
    top_n     : si défini, on ne garde que les `top_n` joueurs les plus
                "connus" (cf. _fame_score) pour éviter d'avoir trop de
                role players obscurs dans le pool. None = tout garder.
    """
    if hist_csv is None:
        hist_csv = os.path.join(
            os.path.dirname(__file__) or ".",
            "player_stats_traditionnal_rs.csv",
        )

    teams_csv = _read_csv(os.path.join(csv_dir, "NBA_TEAMS.csv"))
    players_csv = _read_csv(os.path.join(csv_dir, "NBA_PLAYERS.csv"))
    games_csv = _read_csv(os.path.join(csv_dir, "NBA_PLAYER_GAMES.csv"))

    nick_by_abbr: dict[str, str] = {
        row["abbreviation"]: row["nickname"] for row in teams_csv
    }
    nick_by_abbr.update(HISTORICAL_TEAM_NAMES)

    name_by_id: dict[int, str] = {
        int(row["id"]): row["full_name"] for row in players_csv
    }

    live = _aggregate_player_games(games_csv)

    hist: dict[int, dict] = {}
    if os.path.exists(hist_csv):
        hist = _aggregate_historical(_read_csv(hist_csv))

    all_pids = set(live.keys()) | set(hist.keys())

    players: list[Player] = []
    for pid in all_pids:
        l = live.get(pid)
        h = hist.get(pid)

        l_games = l["games"] if l else 0
        h_games = h["games"] if h else 0
        total_games = l_games + h_games

        # Inclure si : actif en 2024-25 avec assez de matchs,
        # OU carrière historique substantielle (≥ 2 saisons ~ 150 matchs).
        if l_games >= min_games:
            pass
        elif total_games >= 150:
            pass
        else:
            continue

        if pid not in name_by_id:
            continue

        teams = (l["teams"] if l else set()) | (h["teams"] if h else set())
        team_seasons = (
            (l["team_seasons"] if l else set())
            | (h["team_seasons"] if h else set())
        )

        # Patch manuel pour les transactions récentes (Seth Curry, etc.)
        name_for_override = name_by_id.get(pid, "")
        ts_override = TEAM_SEASONS_OVERRIDES.get(name_for_override)
        if ts_override:
            team_seasons = team_seasons | ts_override
            teams = teams | {t for t, _ in ts_override}
        seasons = (
            (l["seasons"] if l else set()) | (h["seasons"] if h else set())
        )

        pts_total = (l["pts_total"] if l else 0.0) + (h["pts_total"] if h else 0.0)
        reb_total = (l["reb_total"] if l else 0.0) + (h["reb_total"] if h else 0.0)
        ast_total = (l["ast_total"] if l else 0.0) + (h["ast_total"] if h else 0.0)

        career_ppg = pts_total / total_games if total_games else 0.0
        career_rpg = reb_total / total_games if total_games else 0.0
        career_apg = ast_total / total_games if total_games else 0.0

        name = name_by_id[pid]
        enrich = ENRICHMENT_BY_NAME.get(name, {})

        players.append(Player(
            id=pid,
            name=name,
            teams=frozenset(teams),
            nationality=enrich.get("nationality", ""),
            awards=enrich.get("awards", frozenset()),
            draft_pick=enrich.get("draft_pick"),
            draft_round=enrich.get("draft_round"),
            career_ppg=career_ppg,
            career_rpg=career_rpg,
            career_apg=career_apg,
            seasons=frozenset(seasons),
            is_champion=enrich.get("is_champion", False),
            team_seasons=frozenset(team_seasons),
        ))

    # Filtre vers les `top_n` joueurs les plus connus pour éviter d'avoir
    # majoritairement des role players obscurs dans le pool.
    if top_n is not None and len(players) > top_n:
        players.sort(key=_fame_score, reverse=True)
        players = players[:top_n]

    categories = _build_categories(players, nick_by_abbr)
    return categories, players


# ─────────────────────────────────────────────────────────────────────────────
# Construction des catégories
# ─────────────────────────────────────────────────────────────────────────────

def _build_categories(
    players: list[Player],
    nick_by_abbr: dict[str, str],
) -> list[Category]:
    cats: list[Category] = []

    # ── TEAM ─────────────────────────────────────────────────────────────────
    abbrs_in_data = {t for p in players for t in p.teams}
    for abbr in sorted(abbrs_in_data):
        nickname = nick_by_abbr.get(abbr, abbr)
        diff = 1 if abbr in POPULAR_TEAMS else (2 if abbr in BIG_MARKET else 3)
        cats.append(Category(
            id=f"team_{abbr.lower()}",
            label=nickname,
            axis=Axis.TEAM,
            difficulty=diff,
            predicate=lambda p, a=abbr: a in p.teams,
        ))

    # ── NATIONALITY ───────────────────────────────────────────────────────────
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

    # ── AWARD ─────────────────────────────────────────────────────────────────
    award_defs = [
        ("award_mvp",        "MVP",              2, "MVP"),
        ("award_finals_mvp", "Finals MVP",        3, "Finals MVP"),
        ("award_dpoy",       "DPOY",              3, "DPOY"),
        ("award_roy",        "Rookie of the Year", 3, "ROY"),
        ("award_6moy",       "Sixth Man",         4, "Sixth Man"),
        ("award_all_star",   "All-Star",          1, "All-Star"),
        ("award_all_nba",    "All-NBA",           2, "All-NBA"),
        ("award_olympic_gold_2024",   "Champion olympique 2024",          3,
         "Olympic Gold 2024"),
        ("award_olympic_silver_fra",  "Médaille argent Paris 2024 (France)", 4,
         "Olympic Silver 2024"),
    ]
    for cid, label, diff, key in award_defs:
        cats.append(Category(
            id=cid, label=label, axis=Axis.AWARD, difficulty=diff,
            predicate=lambda p, k=key: k in p.awards,
        ))

    # ── DRAFT ─────────────────────────────────────────────────────────────────
    cats.extend([
        Category("draft_pick_1", "1er choix de draft", Axis.DRAFT, 3,
                 lambda p: p.draft_pick == 1),
        Category("draft_top_3", "Top 3 de draft", Axis.DRAFT, 2,
                 lambda p: p.draft_pick is not None and p.draft_pick <= 3),
        Category("draft_round_2", "Choix du 2e tour", Axis.DRAFT, 4,
                 lambda p: p.draft_round == 2),
    ])

    # ── STAT (moyennes de carrière) ────────────────────────────────────────────
    cats.extend([
        Category("stat_20_ppg", "20+ PPG (carrière)", Axis.STAT, 2,
                 lambda p: p.career_ppg >= 20.0),
        Category("stat_25_ppg", "25+ PPG (carrière)", Axis.STAT, 3,
                 lambda p: p.career_ppg >= 25.0),
        Category("stat_30_ppg", "30+ PPG (carrière)", Axis.STAT, 5,
                 lambda p: p.career_ppg >= 30.0),
        Category("stat_10_rpg", "10+ RPG (carrière)", Axis.STAT, 4,
                 lambda p: p.career_rpg >= 10.0),
        Category("stat_8_apg",  "8+ APG (carrière)",  Axis.STAT, 4,
                 lambda p: p.career_apg >= 8.0),
    ])

    # ── CAREER ────────────────────────────────────────────────────────────────
    cats.extend([
        Category("career_champion", "Champion NBA", Axis.CAREER, 2,
                 lambda p: p.is_champion),
        Category("career_one_team", "Une seule franchise (carrière)",
                 Axis.CAREER, 3,
                 lambda p: len(p.teams) == 1),
        Category("career_4plus_teams", "Joué pour 4+ franchises",
                 Axis.CAREER, 2,
                 lambda p: len(p.teams) >= 4),
    ])

    # ── ERA ───────────────────────────────────────────────────────────────────
    cats.extend([
        Category("era_1990s", "Actif dans les années 1990", Axis.ERA, 3,
                 lambda p: any(s < 2000 for s in p.seasons)),
        Category("era_2000s", "Actif dans les années 2000", Axis.ERA, 2,
                 lambda p: any(2000 <= s < 2010 for s in p.seasons)),
        Category("era_2010s", "Actif dans les années 2010", Axis.ERA, 1,
                 lambda p: any(2010 <= s < 2020 for s in p.seasons)),
        Category("era_2020s", "Actif dans les années 2020", Axis.ERA, 1,
                 lambda p: any(s >= 2020 for s in p.seasons)),
    ])

    # ── TEAMMATE ──────────────────────────────────────────────────────────────
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

    # ── COMBOS (catégories composées) ─────────────────────────────────────────
    # ~3-8 joueurs par catégorie — difficulté 4-5.
    cats.extend([
        # Jordan, Robinson, Garnett, Giannis, Olajuwon
        Category("combo_mvp_dpoy", "MVP et DPOY", Axis.AWARD, 5,
                 lambda p: "MVP" in p.awards and "DPOY" in p.awards),

        # Shaq, Tim Duncan, LeBron, Robinson, Olajuwon
        Category("combo_pick1_mvp_champ",
                 "Draft #1, MVP et Champion NBA", Axis.AWARD, 5,
                 lambda p: (p.draft_pick == 1
                            and "MVP" in p.awards
                            and p.is_champion)),

        # Jordan, Olajuwon, Giannis, Kawhi
        Category("combo_finals_mvp_dpoy",
                 "Finals MVP et DPOY", Axis.AWARD, 5,
                 lambda p: ("Finals MVP" in p.awards
                            and "DPOY" in p.awards)),

        # Jordan, Magic (hors dataset), LeBron, Shaq, Duncan, Jokić, Giannis, Curry
        Category("combo_mvp_finals_mvp_champ",
                 "MVP, Finals MVP et Champion", Axis.AWARD, 4,
                 lambda p: ("MVP" in p.awards
                            and "Finals MVP" in p.awards
                            and p.is_champion)),

        # LeBron, Durant, Andrew Wiggins, Shaq, Pau Gasol, Vince Carter...
        Category("combo_roy_champ",
                 "ROY et Champion NBA", Axis.AWARD, 4,
                 lambda p: "ROY" in p.awards and p.is_champion),

        # Jokić, Draymond, Ginobili, Marc Gasol, Middleton, Patty Mills…
        Category("combo_r2_champ",
                 "Choix 2e tour + Champion NBA", Axis.DRAFT, 3,
                 lambda p: p.draft_round == 2 and p.is_champion),

        # LeBron, Curry, Durant, Tatum, Jrue, Davis, Caruso, White…
        Category("combo_olympic24_champ",
                 "Champion olympique 2024 et Champion NBA", Axis.AWARD, 4,
                 lambda p: ("Olympic Gold 2024" in p.awards
                            and p.is_champion)),

        # Russell Westbrook, Luka, Trae Young, Haliburton…
        Category("combo_ppg20_apg8",
                 "20+ PPG et 8+ PAS (carrière)", Axis.STAT, 4,
                 lambda p: p.career_ppg >= 20.0 and p.career_apg >= 8.0),

        # Jokić, Sabonis…
        Category("combo_rpg10_apg5",
                 "10+ REB et 5+ PAS (carrière)", Axis.STAT, 5,
                 lambda p: p.career_rpg >= 10.0 and p.career_apg >= 5.0),

        # Jokić, Draymond, Ginobili, Marc Gasol, Isaiah Thomas, Brunson…
        Category("combo_r2_allstar",
                 "Choix 2e tour + All-Star", Axis.DRAFT, 3,
                 lambda p: p.draft_round == 2 and "All-Star" in p.awards),
    ])

    return cats


if __name__ == "__main__":
    csv_dir = "nba_dataset_extracted"
    cats, players = load_real_dataset(csv_dir)
    print(f"Joueurs  : {len(players)}")
    print(f"Catégories : {len(cats)}")
    from collections import Counter
    by_axis = Counter(c.axis.value for c in cats)
    print(f"Par axe  : {dict(by_axis)}")
    enriched = sum(1 for p in players if p.nationality or p.awards)
    print(f"Joueurs enrichis : {enriched}")
    historical_only = sum(
        1 for p in players if p.seasons and min(p.seasons) < 2020
        and max(p.seasons) < 2024
    )
    print(f"Joueurs historiques (inactifs en 2024-25) : {historical_only}")
