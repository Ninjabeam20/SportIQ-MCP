"""Tests for the full-tournament Monte Carlo (flagship engine)."""
from __future__ import annotations

from sportiq.football.adapters.static_seed import load_elo_seed, load_wc2026
from sportiq.football.models.bracket_sim import _seed_order, simulate_tournament

_GROUPS = load_wc2026()["groups"]
_RATINGS = load_elo_seed()


def test_seed_order_keeps_top_seeds_apart():
    # Standard bracket: seeds 1 and 2 land in opposite halves (meet only in final).
    assert _seed_order(4) == [1, 4, 2, 3]
    order8 = _seed_order(8)
    assert sorted(order8) == list(range(1, 9))
    half = len(order8) // 2
    assert 1 in order8[:half] and 2 in order8[half:]


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
