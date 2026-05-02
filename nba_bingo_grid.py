"""
NBA Bingo — Générateur de grille équilibrée.

Implémente l'algorithme en 5 étapes :
    1. Quotas par axe (TEAM, NATIONALITY, AWARD, DRAFT, STAT, CAREER,
       ERA, TEAMMATE)
    2. Quotas par difficulté (1 = très facile → 5 = très dur)
    3. Tirage avec contrainte croisée (axe × difficulté) + backtracking
    4. Filtres anti-redondance (corrélations, équipes "big market")
    5. Validation de faisabilité par simulation Monte Carlo

Mode A multijoueur : génère aussi une séquence de joueurs partagée,
validée par matching biparti pour garantir que la grille reste
résolvable avec cette séquence précise.

Règle de jeu : MAX_STRIKES = 2 erreurs avant défaite (appliqué côté
moteur de partie, pas dans le simulateur de faisabilité qui suppose
un joueur optimal).
"""

from __future__ import annotations

import json
import os
import random
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Modèles
# ─────────────────────────────────────────────────────────────────────────────


class Axis(str, Enum):
    TEAM = "TEAM"
    NATIONALITY = "NATIONALITY"
    AWARD = "AWARD"
    DRAFT = "DRAFT"
    STAT = "STAT"
    CAREER = "CAREER"
    ERA = "ERA"
    TEAMMATE = "TEAMMATE"


@dataclass(frozen=True)
class Player:
    """Un joueur NBA. Champs minimaux nécessaires à la validation."""
    id: int
    name: str
    teams: frozenset[str]
    nationality: str
    awards: frozenset[str]
    draft_pick: Optional[int]   # None = undrafted
    draft_round: Optional[int]
    career_ppg: float
    career_rpg: float
    career_apg: float
    seasons: frozenset[int]     # années de saisons jouées
    is_champion: bool
    # (équipe, année) pour résoudre les catégories TEAMMATE.
    # Optionnel : un joueur sans cette donnée ne validera aucune
    # catégorie "a joué avec X".
    team_seasons: frozenset[tuple[str, int]] = frozenset()


def played_with(p1: Player, p2: Player) -> bool:
    """Vrai si p1 et p2 ont partagé au moins une saison dans la même équipe."""
    return bool(p1.team_seasons & p2.team_seasons)


@dataclass
class Category:
    """
    Une case de la grille. Le prédicat est la source de vérité pour matches().
    pool_size est calculé une fois offline sur tout le dataset.
    """
    id: str
    label: str
    axis: Axis
    difficulty: int             # 1..5
    predicate: Callable[[Player], bool]
    pool_size: int = 0          # rempli par compute_pool_sizes()
    # IDs de catégories trivialement équivalentes (à éviter sur la même grille)
    correlated_with: frozenset[str] = field(default_factory=frozenset)

    def matches(self, player: Player) -> bool:
        return self.predicate(player)


@dataclass
class Grid:
    """Grille 4x4 = 16 cases (sans case libre, comme Football Bingo)."""
    cells: list[Category]

    @property
    def size(self) -> int:
        return len(self.cells)

    def __post_init__(self):
        if len(self.cells) != 16:
            raise ValueError(f"Grid must have 16 cells, got {len(self.cells)}")


# ─────────────────────────────────────────────────────────────────────────────
# Étape 0 — Pré-calcul des pool_size
# ─────────────────────────────────────────────────────────────────────────────


def compute_pool_sizes(categories: list[Category], players: list[Player]) -> None:
    """Remplit Category.pool_size = nb de joueurs du pool qui matchent."""
    for c in categories:
        c.pool_size = sum(1 for p in players if c.matches(p))


def build_match_matrix(
    categories: list[Category], players: list[Player]
) -> list[list[bool]]:
    """Matrice booléenne players × categories pour accélérer la simulation."""
    return [[c.matches(p) for c in categories] for p in players]


# ─────────────────────────────────────────────────────────────────────────────
# Étape 1 + 2 — Tirage des quotas
# ─────────────────────────────────────────────────────────────────────────────

# Quotas cibles (min, max) par axe pour 16 cases.
AXIS_QUOTAS: dict[Axis, tuple[int, int]] = {
    Axis.TEAM:        (5, 6),
    Axis.NATIONALITY: (2, 3),
    Axis.AWARD:       (3, 4),
    Axis.DRAFT:       (1, 2),
    Axis.STAT:        (1, 2),
    Axis.CAREER:      (1, 2),
    Axis.ERA:         (0, 1),
    Axis.TEAMMATE:    (0, 1),
}

# Quotas cibles (min, max) par niveau de difficulté pour 16 cases.
DIFFICULTY_QUOTAS: dict[int, tuple[int, int]] = {
    1: (3, 4),   # très facile (Lakers, USA, MVP générique)
    2: (4, 5),
    3: (4, 5),
    4: (2, 3),
    5: (1, 1),   # exactement 1 case "piège"
}

GRID_SIZE = 16

# Règles de jeu — appliquées côté moteur de partie (frontend / backend),
# pas dans le simulateur de faisabilité (qui modélise un joueur optimal).
MAX_STRIKES = 2                  # affiché en feedback, ne termine plus la partie
TOTAL_PERFECT_SCORE = 60         # score d'une grille parfaitement remplie
SECONDS_PER_TURN = 10            # temps imparti par tour avant auto-skip


def _draw_quotas_summing_to(
    quotas: dict, total: int, rng: random.Random
) -> dict:
    """
    Tire des quotas dans les fourchettes (min, max), en s'assurant
    que la somme = total. Approche : on tire min partout, puis on
    distribue le surplus aléatoirement parmi les axes/diffs ayant
    encore de la marge.
    """
    keys = list(quotas.keys())
    chosen = {k: quotas[k][0] for k in keys}
    remaining = total - sum(chosen.values())

    if remaining < 0:
        raise ValueError(
            f"Sum of mins ({sum(chosen.values())}) exceeds total ({total})"
        )

    # Distribue le surplus
    while remaining > 0:
        candidates = [k for k in keys if chosen[k] < quotas[k][1]]
        if not candidates:
            raise ValueError(
                f"Cannot reach total={total}: sum of maxes is "
                f"{sum(q[1] for q in quotas.values())}"
            )
        k = rng.choice(candidates)
        chosen[k] += 1
        remaining -= 1

    return chosen


# ─────────────────────────────────────────────────────────────────────────────
# Étape 3 + 4 — Génération de la grille avec backtracking
# ─────────────────────────────────────────────────────────────────────────────

# Équipes "big market" : limiter pour éviter qu'une superstar coche 4 cases.
# On accepte les deux conventions de nommage : ancien démo (team_lakers)
# et dataset réel (team_lal).
BIG_MARKET_TEAM_IDS: frozenset[str] = frozenset({
    # Démo
    "team_lakers", "team_warriors", "team_celtics",
    "team_heat", "team_bulls", "team_knicks",
    # Dataset réel (abréviations 3 lettres)
    "team_lal", "team_gsw", "team_bos",
    "team_mia", "team_chi", "team_nyk",
})
MAX_BIG_MARKET_TEAMS = 3


def _is_redundant(
    candidate: Category, picked: list[Category]
) -> bool:
    """Filtres anti-redondance (étape 4)."""
    picked_ids = {c.id for c in picked}

    # Pas de doublon
    if candidate.id in picked_ids:
        return True

    # Pas deux catégories trivialement équivalentes
    if candidate.correlated_with & picked_ids:
        return True

    # Pas plus de MAX_BIG_MARKET_TEAMS équipes big market
    if candidate.id in BIG_MARKET_TEAM_IDS:
        already = sum(1 for c in picked if c.id in BIG_MARKET_TEAM_IDS)
        if already >= MAX_BIG_MARKET_TEAMS:
            return True

    return False


def _generate_grid_attempt(
    categories: list[Category],
    axis_quotas: dict[Axis, int],
    difficulty_quotas: dict[int, int],
    rng: random.Random,
    max_iterations: int = 5_000,
) -> Optional[list[Category]]:
    """
    Une tentative de génération par backtracking CSP.

    Stratégie : à chaque étape, on choisit l'axe encore à pourvoir
    qui a le moins de catégories disponibles (MRV strict). On essaie
    chaque candidat de cet axe, en respectant les quotas de difficulté.
    """
    # Filtre les catégories vides : elles ne peuvent jamais être validées
    usable = [c for c in categories if c.pool_size > 0]

    by_axis: dict[Axis, list[Category]] = {a: [] for a in Axis}
    for c in usable:
        by_axis[c.axis].append(c)

    picked: list[Category] = []
    picked_ids: set[str] = set()
    big_market_count = [0]
    axis_left = dict(axis_quotas)
    diff_left = dict(difficulty_quotas)

    iterations = [0]

    def is_redundant_fast(c: Category) -> bool:
        if c.id in picked_ids:
            return True
        if c.correlated_with & picked_ids:
            return True
        if c.id in BIG_MARKET_TEAM_IDS and big_market_count[0] >= MAX_BIG_MARKET_TEAMS:
            return True
        return False

    def available_for_axis(axis: Axis) -> list[Category]:
        return [
            c for c in by_axis[axis]
            if c.id not in picked_ids
            and diff_left.get(c.difficulty, 0) > 0
            and not is_redundant_fast(c)
        ]

    def backtrack() -> bool:
        iterations[0] += 1
        if iterations[0] > max_iterations:
            return False
        if len(picked) == GRID_SIZE:
            return True

        # MRV : choisis l'axe à pourvoir le plus contraint
        best_axis = None
        best_avail = None
        best_count = float("inf")
        for axis, n_needed in axis_left.items():
            if n_needed <= 0:
                continue
            avail = available_for_axis(axis)
            if len(avail) < n_needed:
                return False  # pruning : insatisfiable
            if len(avail) < best_count:
                best_count = len(avail)
                best_axis = axis
                best_avail = avail

        if best_axis is None:
            return False

        rng.shuffle(best_avail)
        # Limite le branching factor pour éviter l'explosion combinatoire
        for cand in best_avail[:6]:
            picked.append(cand)
            picked_ids.add(cand.id)
            axis_left[best_axis] -= 1
            diff_left[cand.difficulty] -= 1
            is_big = cand.id in BIG_MARKET_TEAM_IDS
            if is_big:
                big_market_count[0] += 1

            if backtrack():
                return True

            picked.pop()
            picked_ids.remove(cand.id)
            axis_left[best_axis] += 1
            diff_left[cand.difficulty] += 1
            if is_big:
                big_market_count[0] -= 1

        return False

    return picked if backtrack() else None


# ─────────────────────────────────────────────────────────────────────────────
# Étape 5 — Validation de faisabilité par simulation Monte Carlo
# ─────────────────────────────────────────────────────────────────────────────


def simulate_solo_completion(
    grid: Grid,
    players: list[Player],
    match_matrix: list[list[bool]],
    category_indices: list[int],
    rng: random.Random,
    max_turns: int = 60,
) -> Optional[int]:
    """
    Simule une partie solo : on tire des joueurs au hasard avec remise,
    et pour chaque joueur on coche la 1re case valide encore vide.
    Retourne le nombre de tours pour compléter, ou None si max_turns dépassé.

    Stratégie gloutonne : à chaque tour, on prend la case valide la plus
    "rare" (pool_size minimum) parmi les cases vides → modélise un joueur
    rationnel qui économise ses joueurs polyvalents.
    """
    cells_done = [False] * GRID_SIZE
    # Pool sizes par cellule (plus petit = case rare → prioritaire)
    rarity = [grid.cells[i].pool_size for i in range(GRID_SIZE)]

    for turn in range(1, max_turns + 1):
        p_idx = rng.randrange(len(players))
        # Trouve les cases valides encore vides pour ce joueur
        valid_cells = [
            i for i in range(GRID_SIZE)
            if not cells_done[i]
            and match_matrix[p_idx][category_indices[i]]
        ]
        if valid_cells:
            # Joue la case la plus rare
            best = min(valid_cells, key=lambda i: rarity[i])
            cells_done[best] = True
            if all(cells_done):
                return turn
    return None


def validate_feasibility(
    grid: Grid,
    players: list[Player],
    match_matrix: list[list[bool]],
    category_indices: list[int],
    rng: random.Random,
    n_simulations: int = 200,
    target_median_range: tuple[int, int] = (18, 35),
    min_completion_rate: float = 0.80,
    max_turns: int = 80,
) -> tuple[bool, dict]:
    """
    Lance n simulations et vérifie que la médiane est dans la fenêtre cible
    et que le taux de complétion dépasse min_completion_rate.

    Note : avec un vrai dataset NBA (600+ joueurs), min_completion_rate
    peut être remonté à 0.95 sans souci.
    """
    results = []
    for _ in range(n_simulations):
        r = simulate_solo_completion(
            grid, players, match_matrix, category_indices, rng,
            max_turns=max_turns,
        )
        if r is not None:
            results.append(r)

    completion_rate = len(results) / n_simulations
    if completion_rate < min_completion_rate:
        return False, {
            "completion_rate": completion_rate,
            "reason": f"completion_rate {completion_rate:.0%} < {min_completion_rate:.0%}",
        }

    results.sort()
    median = results[len(results) // 2]
    p90 = results[int(len(results) * 0.9)]
    lo, hi = target_median_range
    ok = lo <= median <= hi

    return ok, {
        "completion_rate": completion_rate,
        "median_turns": median,
        "p90_turns": p90,
        "min_turns": results[0],
        "max_turns": results[-1],
        "target_range": target_median_range,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Mode A — Séquence partagée pour le multijoueur synchrone
# ─────────────────────────────────────────────────────────────────────────────


def generate_shared_sequence(
    grid: Grid,
    players: list[Player],
    match_matrix: list[list[bool]],
    category_indices: list[int],
    rng: random.Random,
    sequence_length: int = 24,
    max_attempts: int = 50,
) -> Optional[list[int]]:
    """
    Tire une séquence de joueurs UNIQUES couvrant la grille.

    Approche dirigée : pour chaque case, on garantit qu'au moins UN
    joueur valide est dans la séquence (sinon la grille est invalide).
    Puis on complète avec des joueurs aléatoires jusqu'à `sequence_length`.
    Enfin on vérifie via matching biparti glouton qu'une assignation
    1-pour-1 (case ↔ joueur distinct) existe.

    Bien plus fiable qu'un tirage aléatoire pur sur un pool large où
    certaines cases ont 1-2 joueurs valides.
    """
    target_length = min(sequence_length, len(players))
    if target_length < GRID_SIZE:
        return None  # impossible de couvrir 16 cases avec moins de 16 joueurs

    n_players = len(players)
    # Pré-calcul : indices de joueurs valides par case (filtrées par catégorie)
    valid_per_cell = [
        [i for i in range(n_players) if match_matrix[i][cat_idx]]
        for cat_idx in category_indices
    ]
    # Aucune case ne peut avoir 0 joueur valide ici (filtré en amont)
    if any(not v for v in valid_per_cell):
        return None

    for _ in range(max_attempts):
        seq_set: set[int] = set()
        # Étape 1 : pour chaque case, ajouter un joueur valide unique
        cell_order = list(range(GRID_SIZE))
        # On commence par les cases les plus contraintes (peu de joueurs valides)
        cell_order.sort(key=lambda i: len(valid_per_cell[i]))
        for ci in cell_order:
            options = list(valid_per_cell[ci])
            rng.shuffle(options)
            for p_idx in options:
                if p_idx not in seq_set:
                    seq_set.add(p_idx)
                    break
        # Étape 2 : compléter avec des joueurs aléatoires
        remaining = [i for i in range(n_players) if i not in seq_set]
        rng.shuffle(remaining)
        for p_idx in remaining:
            if len(seq_set) >= target_length:
                break
            seq_set.add(p_idx)
        # Étape 3 : permutation aléatoire de l'ordre
        seq = list(seq_set)
        rng.shuffle(seq)
        if _sequence_covers_grid(seq, match_matrix, category_indices):
            return seq
    return None


def _sequence_covers_grid(
    seq: list[int],
    match_matrix: list[list[bool]],
    category_indices: list[int],
) -> bool:
    """
    Matching biparti glouton : peut-on assigner chaque case à un joueur
    distinct de la séquence ? Trie les cases par nb de joueurs valides
    croissant (cases rares en premier = heuristique MRV).
    """
    # Pour chaque case, liste des indices de joueurs valides dans la séquence
    cell_options: list[list[int]] = []
    for cat_idx in category_indices:
        opts = [i for i, p_idx in enumerate(seq) if match_matrix[p_idx][cat_idx]]
        cell_options.append(opts)

    # Trie les cases par nombre d'options croissant
    order = sorted(range(GRID_SIZE), key=lambda i: len(cell_options[i]))

    used: set[int] = set()
    for cell in order:
        # Premier joueur disponible non encore utilisé
        for player_pos in cell_options[cell]:
            if player_pos not in used:
                used.add(player_pos)
                break
        else:
            return False  # aucune option libre → grille non couvrable
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrateur
# ─────────────────────────────────────────────────────────────────────────────


def generate_balanced_grid(
    categories: list[Category],
    players: list[Player],
    rng: Optional[random.Random] = None,
    max_grid_attempts: int = 20,
    with_shared_sequence: bool = True,
    validate_solo: bool = False,
) -> tuple[Grid, dict, Optional[list[int]]]:
    """
    Pipeline complet. Retourne (grid, stats_de_faisabilité, séquence_partagée).

    `validate_solo` (défaut False) : exécute le simulateur Monte Carlo
    qui modélise un joueur solo tirant au hasard. Inutile en mode
    multijoueur où la séquence partagée garantit déjà la solvabilité
    via matching biparti. Activer pour le mode solo classique ou pour
    estimer la difficulté.

    Lève RuntimeError si aucune grille viable n'est trouvée.
    """
    rng = rng or random.Random()

    if any(c.pool_size == 0 for c in categories):
        compute_pool_sizes(categories, players)
    match_matrix = build_match_matrix(categories, players)

    for attempt in range(max_grid_attempts):
        axis_q = _draw_quotas_summing_to(AXIS_QUOTAS, GRID_SIZE, rng)
        diff_q = _draw_quotas_summing_to(DIFFICULTY_QUOTAS, GRID_SIZE, rng)

        cells = _generate_grid_attempt(categories, axis_q, diff_q, rng)
        if cells is None:
            continue

        rng.shuffle(cells)
        grid = Grid(cells=cells)
        cat_indices = [categories.index(c) for c in cells]

        stats: dict = {}
        if validate_solo:
            ok, sim_stats = validate_feasibility(
                grid, players, match_matrix, cat_indices, rng,
            )
            if not ok:
                continue
            stats.update(sim_stats)

        sequence = None
        if with_shared_sequence:
            sequence = generate_shared_sequence(
                grid, players, match_matrix, cat_indices, rng,
            )
            if sequence is None:
                continue
            stats["sequence_length"] = len(sequence)

        stats["grid_attempts"] = attempt + 1
        return grid, stats, sequence

    raise RuntimeError(
        f"No viable grid found after {max_grid_attempts} attempts. "
        "Vérifie ton catalogue de catégories."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Export JSON — alimente le frontend Vue
# ─────────────────────────────────────────────────────────────────────────────


def _build_game_dict(
    grid: Grid,
    players: list[Player],
    sequence: list[int],
    stats: Optional[dict] = None,
) -> dict:
    """Sérialise une partie (grille + séquence) en dict JSON-compatible."""
    cells = [
        {
            "id": c.id,
            "label": c.label,
            "axis": c.axis.value,
            "difficulty": c.difficulty,
        }
        for c in grid.cells
    ]

    seq_data = []
    for p_idx in sequence:
        player = players[p_idx]
        valid = [c.id for c in grid.cells if c.matches(player)]
        seq_data.append({
            "id": player.id,
            "name": player.name,
            "validCellIds": valid,
        })

    game: dict = {"cells": cells, "sequence": seq_data}
    if stats:
        game["stats"] = {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in stats.items()
        }
    return game


def export_games_to_json(
    games: list[dict],
    file_path: str,
) -> None:
    """
    Sérialise une collection de parties vers JSON. Le frontend en pioche
    une au hasard à chaque chargement / "Rejouer".
    """
    output = {
        "rules": {
            "maxStrikes": MAX_STRIKES,
            "gridSize": GRID_SIZE,
            "totalPerfectScore": TOTAL_PERFECT_SCORE,
            "pointsPerCell": TOTAL_PERFECT_SCORE / GRID_SIZE,
            "secondsPerTurn": SECONDS_PER_TURN,
        },
        "games": games,
    }
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# Démo — mini-dataset pour valider que tout tourne
# ─────────────────────────────────────────────────────────────────────────────


def _demo_dataset() -> tuple[list[Category], list[Player]]:
    """Mini-dataset pour démo. Remplace par ta vraie base NBA en prod."""

    # Quelques joueurs représentatifs (NBA 1990+)
    players = [
        Player(1, "LeBron James",
               frozenset({"CLE", "MIA", "LAL"}), "USA",
               frozenset({"MVP", "Finals MVP", "All-Star", "ROY", "All-NBA"}),
               1, 1, 27.0, 7.5, 7.4,
               frozenset(range(2004, 2025)), True),
        Player(2, "Stephen Curry",
               frozenset({"GSW"}), "USA",
               frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA"}),
               7, 1, 24.6, 4.7, 6.5,
               frozenset(range(2010, 2025)), True),
        Player(3, "Tony Parker",
               frozenset({"SAS", "CHA"}), "FRA",
               frozenset({"Finals MVP", "All-Star", "All-NBA"}),
               28, 1, 15.5, 2.7, 5.6,
               frozenset(range(2002, 2019)), True,
               team_seasons=frozenset({("SAS", y) for y in range(2002, 2018)})),
        Player(4, "Nikola Jokic",
               frozenset({"DEN"}), "SRB",
               frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA"}),
               41, 2, 21.0, 10.7, 7.0,
               frozenset(range(2016, 2025)), True),
        Player(5, "Giannis Antetokounmpo",
               frozenset({"MIL"}), "GRC",
               frozenset({"MVP", "Finals MVP", "DPOY", "All-Star", "All-NBA"}),
               15, 1, 23.5, 9.8, 4.7,
               frozenset(range(2014, 2025)), True),
        Player(6, "Kobe Bryant",
               frozenset({"LAL"}), "USA",
               frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA"}),
               13, 1, 25.0, 5.2, 4.7,
               frozenset(range(1997, 2017)), True),
        Player(7, "Tim Duncan",
               frozenset({"SAS"}), "USA",
               frozenset({"MVP", "Finals MVP", "ROY", "All-Star", "All-NBA"}),
               1, 1, 19.0, 10.8, 3.0,
               frozenset(range(1998, 2017)), True,
               team_seasons=frozenset({("SAS", y) for y in range(1997, 2016)})),
        Player(8, "Dirk Nowitzki",
               frozenset({"DAL"}), "DEU",
               frozenset({"MVP", "Finals MVP", "All-Star", "All-NBA"}),
               9, 1, 20.7, 7.5, 2.4,
               frozenset(range(1999, 2020)), True),
        Player(9, "Luka Doncic",
               frozenset({"DAL", "LAL"}), "SVN",
               frozenset({"All-Star", "All-NBA", "ROY"}),
               3, 1, 28.6, 8.7, 8.3,
               frozenset(range(2019, 2025)), False),
        Player(10, "Joel Embiid",
               frozenset({"PHI"}), "CMR",
               frozenset({"MVP", "All-Star", "All-NBA"}),
               3, 1, 27.9, 11.2, 3.6,
               frozenset(range(2017, 2025)), False),
        Player(11, "Shai Gilgeous-Alexander",
               frozenset({"LAC", "OKC"}), "CAN",
               frozenset({"MVP", "All-Star", "All-NBA"}),
               11, 1, 24.0, 5.0, 5.5,
               frozenset(range(2019, 2026)), True),
        Player(12, "Manu Ginobili",
               frozenset({"SAS"}), "ARG",
               frozenset({"All-Star", "Sixth Man"}),
               57, 2, 13.3, 3.5, 3.8,
               frozenset(range(2003, 2019)), True,
               team_seasons=frozenset({("SAS", y) for y in range(2002, 2018)})),
        Player(13, "Pau Gasol",
               frozenset({"MEM", "LAL", "CHI", "SAS", "MIL"}), "ESP",
               frozenset({"All-Star", "ROY"}),
               3, 1, 17.0, 9.2, 3.2,
               frozenset(range(2002, 2020)), True),
        Player(14, "Hakeem Olajuwon",
               frozenset({"HOU", "TOR"}), "NGA",
               frozenset({"MVP", "Finals MVP", "DPOY", "All-Star", "All-NBA"}),
               1, 1, 21.8, 11.1, 2.5,
               frozenset(range(1985, 2003)), True),
        Player(15, "Kawhi Leonard",
               frozenset({"SAS", "TOR", "LAC"}), "USA",
               frozenset({"Finals MVP", "DPOY", "All-Star", "All-NBA"}),
               15, 1, 19.6, 6.4, 3.0,
               frozenset(range(2012, 2025)), True,
               team_seasons=frozenset(
                   {("SAS", y) for y in range(2011, 2018)}
                   | {("TOR", 2018)}
                   | {("LAC", y) for y in range(2019, 2025)}
               )),
        Player(16, "Kevin Durant",
               frozenset({"OKC", "GSW", "BKN", "PHX", "HOU"}), "USA",
               frozenset({"MVP", "Finals MVP", "ROY", "All-Star", "All-NBA"}),
               2, 1, 27.3, 7.0, 4.4,
               frozenset(range(2008, 2026)), True),
        Player(17, "Damian Lillard",
               frozenset({"POR", "MIL"}), "USA",
               frozenset({"All-Star", "All-NBA", "ROY"}),
               6, 1, 25.0, 4.2, 6.7,
               frozenset(range(2013, 2025)), False),
        Player(18, "Rudy Gobert",
               frozenset({"UTA", "MIN"}), "FRA",
               frozenset({"DPOY", "All-Star", "All-NBA"}),
               27, 1, 12.5, 11.7, 1.4,
               frozenset(range(2014, 2025)), False),
        Player(19, "Marc Gasol",
               frozenset({"MEM", "TOR", "LAL"}), "ESP",
               frozenset({"DPOY", "All-Star"}),
               48, 2, 14.0, 7.4, 3.4,
               frozenset(range(2009, 2021)), True),
        Player(20, "Ben Wallace",
               frozenset({"WAS", "ORL", "DET", "CHI", "CLE"}), "USA",
               frozenset({"DPOY", "All-Star"}),
               None, None, 5.7, 9.6, 1.3,  # undrafted
               frozenset(range(1997, 2012)), True),
    ]

    # Catalogue de catégories. En prod tu en aurais ~150.
    categories = [
        # ─── TEAM ───
        Category("team_lakers", "Lakers", Axis.TEAM, 1,
                 lambda p: "LAL" in p.teams),
        Category("team_warriors", "Warriors", Axis.TEAM, 1,
                 lambda p: "GSW" in p.teams),
        Category("team_celtics", "Celtics", Axis.TEAM, 2,
                 lambda p: "BOS" in p.teams),
        Category("team_heat", "Heat", Axis.TEAM, 2,
                 lambda p: "MIA" in p.teams),
        Category("team_bulls", "Bulls", Axis.TEAM, 2,
                 lambda p: "CHI" in p.teams),
        Category("team_spurs", "Spurs", Axis.TEAM, 2,
                 lambda p: "SAS" in p.teams),
        Category("team_nuggets", "Nuggets", Axis.TEAM, 3,
                 lambda p: "DEN" in p.teams),
        Category("team_mavs", "Mavericks", Axis.TEAM, 3,
                 lambda p: "DAL" in p.teams),
        Category("team_thunder", "Thunder/OKC", Axis.TEAM, 3,
                 lambda p: "OKC" in p.teams),
        Category("team_grizzlies", "Grizzlies", Axis.TEAM, 3,
                 lambda p: "MEM" in p.teams),
        Category("team_raptors", "Raptors", Axis.TEAM, 3,
                 lambda p: "TOR" in p.teams),
        Category("team_sixers", "76ers", Axis.TEAM, 2,
                 lambda p: "PHI" in p.teams),
        Category("team_bucks", "Bucks", Axis.TEAM, 2,
                 lambda p: "MIL" in p.teams),
        Category("team_clippers", "Clippers", Axis.TEAM, 3,
                 lambda p: "LAC" in p.teams),

        # ─── NATIONALITY ───
        Category("nat_usa", "USA", Axis.NATIONALITY, 1,
                 lambda p: p.nationality == "USA"),
        Category("nat_fra", "France", Axis.NATIONALITY, 3,
                 lambda p: p.nationality == "FRA"),
        Category("nat_can", "Canada", Axis.NATIONALITY, 3,
                 lambda p: p.nationality == "CAN"),
        Category("nat_srb", "Serbie", Axis.NATIONALITY, 4,
                 lambda p: p.nationality == "SRB"),
        Category("nat_grc", "Grèce", Axis.NATIONALITY, 4,
                 lambda p: p.nationality == "GRC"),
        Category("nat_esp", "Espagne", Axis.NATIONALITY, 3,
                 lambda p: p.nationality == "ESP"),
        Category("nat_svn", "Slovénie", Axis.NATIONALITY, 5,
                 lambda p: p.nationality == "SVN"),
        Category("nat_deu", "Allemagne", Axis.NATIONALITY, 4,
                 lambda p: p.nationality == "DEU"),

        # ─── AWARD ───
        Category("award_mvp", "MVP", Axis.AWARD, 2,
                 lambda p: "MVP" in p.awards,
                 correlated_with=frozenset({"award_all_nba"})),
        Category("award_finals_mvp", "Finals MVP", Axis.AWARD, 3,
                 lambda p: "Finals MVP" in p.awards),
        Category("award_dpoy", "DPOY", Axis.AWARD, 3,
                 lambda p: "DPOY" in p.awards),
        Category("award_roy", "Rookie of the Year", Axis.AWARD, 3,
                 lambda p: "ROY" in p.awards),
        Category("award_6moy", "Sixth Man", Axis.AWARD, 4,
                 lambda p: "Sixth Man" in p.awards),
        Category("award_all_star", "All-Star", Axis.AWARD, 1,
                 lambda p: "All-Star" in p.awards),
        Category("award_all_nba", "All-NBA", Axis.AWARD, 2,
                 lambda p: "All-NBA" in p.awards,
                 correlated_with=frozenset({"award_mvp"})),

        # ─── DRAFT ───
        Category("draft_pick_1", "1er choix de draft", Axis.DRAFT, 3,
                 lambda p: p.draft_pick == 1),
        Category("draft_top_3", "Top 3 draft", Axis.DRAFT, 2,
                 lambda p: p.draft_pick is not None and p.draft_pick <= 3),
        Category("draft_round_2", "Second tour", Axis.DRAFT, 3,
                 lambda p: p.draft_round == 2),
        Category("draft_undrafted", "Non-drafté", Axis.DRAFT, 5,
                 lambda p: p.draft_pick is None),

        # ─── STAT ───
        Category("stat_25_ppg", "25+ PPG en carrière", Axis.STAT, 3,
                 lambda p: p.career_ppg >= 25.0),
        Category("stat_10_rpg", "10+ RPG en carrière", Axis.STAT, 4,
                 lambda p: p.career_rpg >= 10.0),
        Category("stat_7_apg", "7+ APG en carrière", Axis.STAT, 4,
                 lambda p: p.career_apg >= 7.0),

        # ─── CAREER ───
        Category("career_champion", "Champion NBA", Axis.CAREER, 2,
                 lambda p: p.is_champion),
        Category("career_one_team", "One-team player", Axis.CAREER, 4,
                 lambda p: len(p.teams) == 1),
        Category("career_5_teams", "A joué pour 5+ équipes", Axis.CAREER, 4,
                 lambda p: len(p.teams) >= 5),

        # ─── ERA ───
        Category("era_1990s", "A joué dans les années 90", Axis.ERA, 3,
                 lambda p: any(1990 <= s <= 1999 for s in p.seasons)),
        Category("era_2020s", "Actif dans les années 2020", Axis.ERA, 1,
                 lambda p: any(s >= 2020 for s in p.seasons)),
    ]

    # ─── TEAMMATE ───
    # Construit après les players pour pouvoir capturer team_seasons.
    duncan_pairs = players[6].team_seasons
    categories.append(
        Category("teammate_duncan", "A joué avec Tim Duncan",
                 Axis.TEAMMATE, 3,
                 lambda p, t=duncan_pairs: bool(p.team_seasons & t))
    )

    return categories, players


_AXIS_SHORT: dict[Axis, str] = {
    Axis.TEAM: "TEAM",
    Axis.TEAMMATE: "MATE",
    Axis.NATIONALITY: "NATI",
    Axis.AWARD: "AWAR",
    Axis.DRAFT: "DRAF",
    Axis.STAT: "STAT",
    Axis.CAREER: "CARE",
    Axis.ERA: "ERA",
}


def _print_grid(grid: Grid) -> None:
    print()
    print("┌" + "─" * 78 + "┐")
    for row in range(4):
        line = "│"
        for col in range(4):
            cat = grid.cells[row * 4 + col]
            tag = f"[D{cat.difficulty}/{_AXIS_SHORT[cat.axis]}]"
            label = (cat.label[:14]).ljust(14)
            line += f" {label} {tag}".ljust(20) + "│"
        print(line)
        if row < 3:
            print("├" + "─" * 78 + "┤")
    print("└" + "─" * 78 + "┘")


NUM_GAMES_TO_EXPORT = 20
NBA_DATASET_DIR = "nba_dataset_extracted"


if __name__ == "__main__":
    if os.path.isdir(NBA_DATASET_DIR):
        from nba_dataset_loader import load_real_dataset
        categories, players = load_real_dataset(NBA_DATASET_DIR)
        source = "réel (CSV 2024-25)"
    else:
        categories, players = _demo_dataset()
        source = "démo (20 joueurs)"

    # Pas de seed : chaque run produit des grilles différentes.
    rng = random.Random()

    print(f"📁 Dataset {source} : {len(players)} joueurs, {len(categories)} catégories")
    compute_pool_sizes(categories, players)

    empty = [c.id for c in categories if c.pool_size == 0]
    if empty:
        print(f"⚠️  Catégories vides dans le pool : {empty}")

    axis_counts = Counter(c.axis for c in categories)
    print(f"📐 Catégories par axe : {dict(axis_counts)}")

    print(f"\n🎲 Génération de {NUM_GAMES_TO_EXPORT} parties...")
    games = []
    for i in range(NUM_GAMES_TO_EXPORT):
        try:
            grid, stats, sequence = generate_balanced_grid(
                categories, players, rng=rng, with_shared_sequence=True,
            )
        except RuntimeError as e:
            print(f"   ⚠️  Partie {i + 1} échouée : {e}")
            continue
        if not sequence:
            continue
        games.append(_build_game_dict(grid, players, sequence, stats=stats))
        diffs = Counter(c.difficulty for c in grid.cells)
        axes = Counter(c.axis.value for c in grid.cells)
        suffix = (f", médiane {stats['median_turns']}t"
                  if "median_turns" in stats else "")
        print(
            f"   ✓ Partie {i + 1} — {len(sequence)} joueurs, "
            f"axes {dict(axes)}, diffs {dict(sorted(diffs.items()))}{suffix}"
        )

    if not games:
        print("❌ Aucune partie générée. Vérifie le catalogue de catégories.")
        raise SystemExit(1)

    # Aperçu de la première grille pour debug
    print()
    print("Aperçu de la première grille :")
    cells_first = [
        Category(
            id=c["id"], label=c["label"],
            axis=Axis(c["axis"]), difficulty=c["difficulty"],
            predicate=lambda _p: False,
        )
        for c in games[0]["cells"]
    ]
    _print_grid(Grid(cells=cells_first))

    out_path = "frontend/public/game.json"
    export_games_to_json(games, out_path)
    print(f"\n💾 {len(games)} parties exportées vers {out_path}")
    print(f"   Score parfait par grille : {TOTAL_PERFECT_SCORE} pts")
