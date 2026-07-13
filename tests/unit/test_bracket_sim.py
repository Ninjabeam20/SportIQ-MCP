"""Tests for the full-tournament Monte Carlo (flagship engine)."""
from __future__ import annotations

from sportiq.football.adapters.static_seed import load_elo_seed, load_wc2026
from sportiq.football.models.bracket_sim import simulate_tournament

_GROUPS = load_wc2026()["groups"]
_RATINGS = load_elo_seed()


def test_exactly_32_qualify_each_iteration():
    # reach_r32 mass across all teams equals the 32 knockout slots
    # (tolerance covers the per-team rounding to 4 decimals).
    sim = simulate_tournament(_GROUPS, _RATINGS, n_iter=1500, seed=1)
    slot_sum = sum(t["reach_r32"] for t in sim["teams"].values())
    assert abs(slot_sum - 32.0) < 0.01


def test_exactly_one_champion_each_iteration():
    sim = simulate_tournament(_GROUPS, _RATINGS, n_iter=1500, seed=1)
    win_mass = sum(t["win"] for t in sim["teams"].values())
    assert abs(win_mass - 1.0) < 0.01


def test_round_probabilities_are_monotone():
    # Reaching a later round implies reaching every earlier one.
    sim = simulate_tournament(_GROUPS, _RATINGS, n_iter=1500, seed=2)
    for t in sim["teams"].values():
        assert t["reach_r32"] >= t["reach_r16"] >= t["reach_qf"] >= t["reach_sf"]
        assert t["reach_sf"] >= t["reach_final"] >= t["win"]


def test_convergence_stable_across_seeds():
    # The champion's title probability is stable (well within ±2%) between seeds.
    a = simulate_tournament(_GROUPS, _RATINGS, n_iter=4000, seed=1)
    b = simulate_tournament(_GROUPS, _RATINGS, n_iter=4000, seed=2)
    champ = a["champion"]
    assert abs(a["teams"][champ]["win"] - b["teams"][champ]["win"]) < 0.02


def test_seeded_runs_reproducible():
    a = simulate_tournament(_GROUPS, _RATINGS, n_iter=800, seed=42)
    b = simulate_tournament(_GROUPS, _RATINGS, n_iter=800, seed=42)
    assert a == b


def test_r32_uses_official_group_position_pairings():
    # One deterministic tournament; collect the actual R32 matchups and confirm they are the
    # official group-position pairings (e.g. 2A vs 2B exists), not a global strength ladder.
    import numpy as np

    from sportiq.football.models import bracket_sim

    rng = np.random.default_rng(7)
    winners, runners, thirds = bracket_sim._draw_qualifiers(rng, _GROUPS, _RATINGS)
    current = bracket_sim._build_r32(winners, runners, thirds)
    assert len(current) == 32
    # Match 73 is "2A vs 2B": runners-up of A and B must be adjacent somewhere in the array.
    pairs = {(current[i], current[i + 1]) for i in range(0, 32, 2)}
    assert (runners["A"], runners["B"]) in pairs or (runners["B"], runners["A"]) in pairs


def test_draw_qualifiers_rejects_non_four_team_group():
    """A group that isn't exactly 4 teams fails loudly instead of an IndexError."""
    import numpy as np
    import pytest

    from sportiq.football.models import bracket_sim

    rng = np.random.default_rng(0)
    bad_groups = {"A": ["X", "Y", "Z"]}  # only 3 teams
    ratings = {"X": 1500.0, "Y": 1500.0, "Z": 1500.0}
    with pytest.raises(ValueError):
        bracket_sim._draw_qualifiers(rng, bad_groups, ratings)


def test_tournament_reports_model_rating_tiebreak_fallbacks():
    sim = simulate_tournament(_GROUPS, _RATINGS, n_iter=50, seed=3)

    assert "tiebreak_fallbacks" in sim
    assert isinstance(sim["tiebreak_fallbacks"], int)
    assert sim["tiebreak_fallbacks"] >= 0
