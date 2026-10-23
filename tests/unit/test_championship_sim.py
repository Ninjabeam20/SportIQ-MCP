"""F1 championship Monte Carlo + exact elimination maths (pure model)."""

from __future__ import annotations

import pytest

from sportiq.f1.models.championship_sim import max_remaining_points, simulate_championship


def _rows(*pairs: tuple[str, float]) -> list[dict]:
    return [{"code": code, "points": pts} for code, pts in pairs]


def _gps(n: int, sprints: int = 0) -> list[dict]:
    return [{"round": 100 + i, "sprint": i < sprints} for i in range(n)]


def test_max_remaining_points_seven_gps_no_sprints_is_175():
    assert max_remaining_points(_gps(7), year=2026) == 175


def test_max_remaining_points_counts_sprint_and_pre_2025_fastest_lap():
    assert max_remaining_points(_gps(1, sprints=1), year=2026) == 33
    assert max_remaining_points(_gps(1), year=2024) == 26


def test_eliminated_driver_has_zero_title_prob():
    # 3 GPs left = 75 max; TSU trails by 100 → cannot win.
    out = simulate_championship(
        _rows(("NOR", 300.0), ("PIA", 290.0), ("TSU", 200.0)),
        _gps(3),
        year=2026,
        n_iter=2000,
        seed=7,
        rounds_completed=20,
    )
    tsu = next(d for d in out["drivers"] if d["code"] == "TSU")
    assert tsu["eliminated"] is True
    assert tsu["title_prob"] == 0.0
    assert tsu["max_possible"] == 275.0


def test_title_probs_sum_to_one():
    out = simulate_championship(
        _rows(("NOR", 300.0), ("PIA", 290.0), ("VER", 280.0), ("RUS", 250.0)),
        _gps(6, sprints=1),
        year=2026,
        n_iter=3000,
        seed=1,
        rounds_completed=17,
    )
    assert sum(d["title_prob"] for d in out["drivers"]) == pytest.approx(1.0, abs=1e-3)
    assert out["rounds_remaining"] == 6
    assert out["max_remaining_points"] == 6 * 25 + 8


def test_championship_sim_is_deterministic_with_seed():
    kwargs = dict(year=2026, n_iter=2000, seed=42, rounds_completed=17)
    rows = _rows(("NOR", 300.0), ("PIA", 290.0), ("VER", 280.0))
    assert simulate_championship(rows, _gps(6), **kwargs) == simulate_championship(
        rows, _gps(6), **kwargs
    )


def test_clinched_title_returns_prob_one():
    # Lead of 100 with 3 GPs (75 max) left: title already decided.
    out = simulate_championship(
        _rows(("NOR", 400.0), ("PIA", 300.0), ("VER", 290.0)),
        _gps(3),
        year=2026,
        n_iter=1000,
        seed=3,
        rounds_completed=21,
    )
    leader = out["drivers"][0]
    assert leader["code"] == "NOR"
    assert leader["title_prob"] == 1.0
    assert all(d["eliminated"] for d in out["drivers"][1:])


def test_no_rounds_remaining_awards_title_to_leader():
    out = simulate_championship(
        _rows(("NOR", 400.0), ("PIA", 390.0)),
        [],
        year=2026,
        n_iter=1000,
        seed=0,
        rounds_completed=24,
    )
    assert out["drivers"][0]["code"] == "NOR"
    assert out["drivers"][0]["title_prob"] == 1.0
    assert out["rounds_remaining"] == 0
