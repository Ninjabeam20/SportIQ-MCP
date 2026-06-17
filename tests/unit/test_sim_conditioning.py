"""Unit tests for conditioning the group + bracket sims on real results."""
from __future__ import annotations

import numpy as np

from sportiq.football.models.bracket_sim import simulate_tournament
from sportiq.football.models.group_sim import simulate_group, simulate_group_once
from sportiq.football.models.results_state import GroupResults, ResultsState

_TEAMS = ["ARG", "COL", "ECU", "CIV"]
_RATINGS = {"ARG": 2090, "COL": 1800, "ECU": 1750, "CIV": 1650}


def _full_group_results() -> GroupResults:
    """All six matches played, contrived so CIV wins the group outright."""
    completed = [
        ("ARG", "COL", 0, 1),
        ("ARG", "ECU", 0, 1),
        ("ARG", "CIV", 0, 3),  # ARG loses all three -> eliminated
        ("COL", "ECU", 1, 1),
        ("COL", "CIV", 0, 2),
        ("ECU", "CIV", 0, 2),  # CIV wins all three
    ]
    return GroupResults(completed=completed, remaining=[])


def test_fully_played_group_is_deterministic():
    """With every match locked, the standings ignore the RNG and the ratings."""
    known = _full_group_results()
    out = simulate_group(_TEAMS, _RATINGS, n_iter=50, seed=1, known=known)
    # CIV (max points) always advances; ARG (lost all) never does.
    assert out["teams"]["CIV"]["p_first"] == 1.0
    assert out["teams"]["ARG"]["p_advance"] == 0.0


def test_eliminated_team_has_zero_advance():
    """A team that has already lost the two matches it needed can't advance."""
    # ARG lost to COL and ECU; only ARG-CIV remains. ARG max 3 pts, but COL & ECU
    # both already have wins over ARG and a draw between them -> ARG can't reach top 2.
    completed = [
        ("ARG", "COL", 0, 2),
        ("ARG", "ECU", 0, 2),
        ("COL", "ECU", 1, 1),
    ]
    remaining = [("ARG", "CIV"), ("COL", "CIV"), ("ECU", "CIV")]
    known = GroupResults(completed=completed, remaining=remaining)
    out = simulate_group(_TEAMS, _RATINGS, n_iter=500, seed=7, known=known)
    assert out["teams"]["ARG"]["p_advance"] == 0.0


def test_known_none_matches_original_behaviour():
    """Passing known=None reproduces the from-scratch sim exactly."""
    rng_a = np.random.default_rng(42)
    rng_b = np.random.default_rng(42)
    a = simulate_group_once(rng_a, _TEAMS, _RATINGS)
    b = simulate_group_once(rng_b, _TEAMS, _RATINGS, None)
    assert a == b


def test_bracket_conditioning_zeros_eliminated_team():
    """An eliminated group team has win probability 0 in the full tournament sim."""
    groups = {
        "A": ["ARG", "COL", "ECU", "CIV"],
        "B": ["FRA", "MAR", "CAN", "PER"],
        "C": ["ESP", "USA", "NOR", "CMR"],
        "D": ["ENG", "SUI", "POL", "PAR"],
        "E": ["BRA", "MEX", "IRN", "CRC"],
        "F": ["POR", "DEN", "WAL", "GHA"],
        "G": ["NED", "JPN", "ALG", "SAU"],
        "H": ["BEL", "SEN", "AUS", "QAT"],
        "I": ["ITA", "AUT", "NGA", "PAN"],
        "J": ["GER", "KOR", "SCO", "JAM"],
        "K": ["CRO", "SRB", "TUN", "UZB"],
        "L": ["URU", "UKR", "EGY", "NZL"],
    }
    ratings = {t: 1700 for teams in groups.values() for t in teams}
    ratings["ARG"] = 2090
    # ARG loses all three group games -> eliminated; group A others outscore it.
    group_a = GroupResults(
        completed=[
            ("ARG", "COL", 0, 1),
            ("ARG", "ECU", 0, 1),
            ("ARG", "CIV", 0, 1),
            ("COL", "ECU", 1, 1),
            ("COL", "CIV", 1, 1),
            ("ECU", "CIV", 1, 1),
        ],
        remaining=[],
    )
    state = ResultsState(groups={"A": group_a})
    out = simulate_tournament(groups, ratings, n_iter=300, seed=3, results=state)
    assert out["teams"]["ARG"]["win"] == 0.0
    assert out["teams"]["ARG"]["reach_r32"] == 0.0
