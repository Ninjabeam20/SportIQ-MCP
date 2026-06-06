"""Tests for the group-stage Monte Carlo."""
from __future__ import annotations

import numpy as np
import pytest

from sportiq.football.models.group_sim import simulate_group, simulate_group_once

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
