"""Tests for the group-stage Monte Carlo."""
from __future__ import annotations

import numpy as np
import pytest

from sportiq.football.models import group_sim
from sportiq.football.models.group_sim import (
    simulate_group,
    simulate_group_once,
    simulate_group_stage,
)
from sportiq.football.models.results_state import GroupResults

_TEAMS = ["AAA", "BBB", "CCC", "DDD"]
_RATINGS = {"AAA": 2000, "BBB": 1800, "CCC": 1700, "DDD": 1500}


def test_group_once_returns_full_ranking():
    rng = np.random.default_rng(0)
    standings = simulate_group_once(rng, _TEAMS, _RATINGS)
    assert len(standings) == 4
    assert [r["rank"] for r in standings] == [1, 2, 3, 4]
    assert {r["team"] for r in standings} == set(_TEAMS)


def test_advance_mass_sums_to_two():
    # Exactly two teams advance every iteration -> p_advance must sum to ~2.
    sim = simulate_group(_TEAMS, _RATINGS, n_iter=3000, seed=1)
    total = sum(t["p_advance"] for t in sim["teams"].values())
    assert abs(total - 2.0) < 0.01  # tol covers per-team 4dp rounding


def test_each_team_position_mass_sums_to_one():
    sim = simulate_group(_TEAMS, _RATINGS, n_iter=2000, seed=2)
    for stats in sim["teams"].values():
        mass = stats["p_first"] + stats["p_second"] + stats["p_third"] + stats["p_fourth"]
        assert abs(mass - 1.0) < 0.01  # tol covers per-team 4dp rounding


def test_strongest_team_most_likely_to_top_group():
    sim = simulate_group(_TEAMS, _RATINGS, n_iter=3000, seed=3)
    top = max(sim["teams"].items(), key=lambda kv: kv[1]["p_first"])[0]
    assert top == "AAA"


def test_seeded_runs_are_reproducible():
    a = simulate_group(_TEAMS, _RATINGS, n_iter=1000, seed=7)
    b = simulate_group(_TEAMS, _RATINGS, n_iter=1000, seed=7)
    assert a == b


def test_simulate_group_rejects_non_four_team_group():
    """A group that isn't exactly 4 teams fails loudly instead of an IndexError."""
    with pytest.raises(ValueError):
        simulate_group(["AAA", "BBB", "CCC"], _RATINGS, n_iter=10, seed=1)


def test_head_to_head_points_precede_overall_goal_difference():
    known = GroupResults(
        completed=[
            ("AAA", "BBB", 1, 0),
            ("AAA", "CCC", 0, 0),
            ("AAA", "DDD", 0, 1),
            ("BBB", "CCC", 10, 0),
            ("BBB", "DDD", 0, 0),
            ("CCC", "DDD", 0, 1),
        ],
        remaining=[],
    )

    standings = simulate_group_once(
        np.random.default_rng(1), _TEAMS, _RATINGS, known
    )
    positions = {row["team"]: row["rank"] for row in standings}

    assert positions["AAA"] < positions["BBB"]


def test_head_to_head_goal_difference_precedes_overall_goal_difference():
    known = GroupResults(
        completed=[
            ("AAA", "BBB", 1, 0),
            ("BBB", "CCC", 3, 0),
            ("CCC", "AAA", 2, 0),
            ("AAA", "DDD", 10, 0),
            ("BBB", "DDD", 1, 0),
            ("CCC", "DDD", 1, 0),
        ],
        remaining=[],
    )

    standings = simulate_group_once(
        np.random.default_rng(1), _TEAMS, _RATINGS, known
    )
    positions = {row["team"]: row["rank"] for row in standings}

    assert positions["BBB"] < positions["AAA"]


def test_unavailable_tiebreak_fields_use_rating_and_are_marked():
    known = GroupResults(
        completed=[
            (a, b, 0, 0)
            for index, a in enumerate(_TEAMS)
            for b in _TEAMS[index + 1 :]
        ],
        remaining=[],
    )

    standings = simulate_group_once(
        np.random.default_rng(1), _TEAMS, _RATINGS, known
    )

    assert [row["team"] for row in standings] == ["AAA", "BBB", "CCC", "DDD"]
    assert all(row["tiebreak_fallback"] for row in standings)


def test_full_group_stage_qualification_mass_is_24_plus_8():
    groups = {
        letter: [f"{letter}{number}" for number in range(1, 5)]
        for letter in "ABCDEFGHIJKL"
    }
    ratings = {
        team: 1600 - index
        for index, team in enumerate(team for teams in groups.values() for team in teams)
    }

    out = simulate_group_stage(groups, ratings, n_iter=200, seed=7)

    assert sum(row["p_auto_advance"] for row in out["teams"].values()) == pytest.approx(
        24, abs=0.02
    )
    assert sum(
        row["p_best_third_advance"] for row in out["teams"].values()
    ) == pytest.approx(8, abs=0.02)
    assert sum(row["p_advance"] for row in out["teams"].values()) == pytest.approx(
        32, abs=0.02
    )


def test_best_third_tie_uses_rating_before_rng_and_is_counted():
    thirds = [
        {"team": "LOW", "group": "A", "points": 4, "gd": 0, "gf": 2},
        {"team": "HIGH", "group": "B", "points": 4, "gd": 0, "gf": 2},
    ]

    ranked, fallback_rows = group_sim._rank_thirds(
        np.random.default_rng(9), thirds, {"LOW": 1400, "HIGH": 1800}
    )

    assert [row["team"] for row in ranked] == ["HIGH", "LOW"]
    assert fallback_rows == 2
