"""dream11_solver — constraint-by-constraint coverage + end-to-end."""

from __future__ import annotations

import pytest

from sportiq.core.errors import InvalidInputError
from sportiq.cricket.models.dream11_solver import solve


def _candidate(name, role, credits, pp, team):
    return {
        "name": name,
        "role": role,
        "credits": credits,
        "projected_points": pp,
        "team": team,
    }


def _synthetic_pool() -> list[dict]:
    """22 candidates spread across two IPL franchises with workable role mix."""
    a_players = [
        _candidate("A_Bat1", "BAT", 10.5, 90, "A"),
        _candidate("A_Bat2", "BAT", 9.0, 75, "A"),
        _candidate("A_Bat3", "BAT", 8.5, 60, "A"),
        _candidate("A_All1", "ALL", 9.5, 88, "A"),
        _candidate("A_All2", "ALL", 8.0, 65, "A"),
        _candidate("A_WK", "WK-BAT", 9.0, 78, "A"),
        _candidate("A_Bowl1", "BOWL", 10.0, 95, "A"),
        _candidate("A_Bowl2", "BOWL", 9.0, 72, "A"),
        _candidate("A_Bowl3", "BOWL", 8.0, 58, "A"),
        _candidate("A_Bowl4", "BOWL", 7.5, 50, "A"),
        _candidate("A_Bat4", "BAT", 7.0, 45, "A"),
    ]
    b_players = [
        _candidate("B_Bat1", "BAT", 10.0, 85, "B"),
        _candidate("B_Bat2", "BAT", 9.5, 80, "B"),
        _candidate("B_Bat3", "BAT", 8.0, 55, "B"),
        _candidate("B_All1", "ALL", 9.0, 82, "B"),
        _candidate("B_All2", "ALL", 8.5, 70, "B"),
        _candidate("B_WK", "WK-BAT", 9.0, 76, "B"),
        _candidate("B_Bowl1", "BOWL", 9.5, 90, "B"),
        _candidate("B_Bowl2", "BOWL", 8.5, 68, "B"),
        _candidate("B_Bowl3", "BOWL", 8.0, 60, "B"),
        _candidate("B_Bowl4", "BOWL", 7.5, 52, "B"),
        _candidate("B_Bat4", "BAT", 7.0, 42, "B"),
    ]
    return a_players + b_players


def test_solver_returns_exactly_11_players():
    result = solve(_synthetic_pool())
    assert len(result["players"]) == 11


def test_solver_respects_credit_cap():
    result = solve(_synthetic_pool())
    assert result["total_credits"] <= 100


def test_solver_respects_team_cap_seven():
    result = solve(_synthetic_pool())
    teams = [p["team"] for p in result["players"]]
    for team in set(teams):
        assert teams.count(team) <= 7


def test_solver_satisfies_role_mix():
    result = solve(_synthetic_pool())
    roles = [p["role"] for p in result["players"]]
    wk = sum(1 for r in roles if r in {"WK-BAT", "WK"})
    bat = sum(1 for r in roles if r == "BAT")
    al = sum(1 for r in roles if r == "ALL")
    bowl = sum(1 for r in roles if r == "BOWL")
    assert 1 <= wk <= 4
    assert 3 <= bat <= 5
    assert 1 <= al <= 3
    assert 3 <= bowl <= 5


def test_captain_and_vice_captain_in_xi_and_distinct():
    result = solve(_synthetic_pool())
    names = {p["name"] for p in result["players"]}
    assert result["captain"] in names
    assert result["vice_captain"] in names
    assert result["captain"] != result["vice_captain"]


def test_total_projected_points_includes_captain_and_vc_boosts():
    pool = _synthetic_pool()
    result = solve(pool)
    base = sum(p["projected_points"] for p in result["players"])
    cap_pp = next(p["projected_points"] for p in pool if p["name"] == result["captain"])
    vc_pp = next(p["projected_points"] for p in pool if p["name"] == result["vice_captain"])
    expected = base + cap_pp * 1.0 + vc_pp * 0.5
    assert result["total_projected_points"] == round(expected, 2)


def test_solver_raises_when_fewer_than_11_candidates():
    with pytest.raises(InvalidInputError):
        solve([_candidate(f"P{i}", "BAT", 8.0, 50, "A") for i in range(10)])


def test_solver_raises_when_credit_cap_unsatisfiable():
    # Every candidate costs 11 credits — XI cost > 100 → infeasible.
    pool = []
    for i in range(22):
        team = "A" if i < 11 else "B"
        role = ["BAT", "BAT", "BAT", "BAT", "ALL", "ALL", "WK-BAT", "BOWL", "BOWL", "BOWL", "BOWL"][i % 11]
        pool.append(_candidate(f"P{i}", role, 11.0, 50, team))
    with pytest.raises(InvalidInputError):
        solve(pool)


def test_solver_raises_when_no_wk_in_pool():
    # No keeper anywhere → role_min_WK-BAT >= 1 unsatisfiable.
    pool = []
    for i in range(22):
        team = "A" if i < 11 else "B"
        role = ["BAT", "BAT", "BAT", "BAT", "BAT", "ALL", "ALL", "BOWL", "BOWL", "BOWL", "BOWL"][i % 11]
        pool.append(_candidate(f"P{i}", role, 8.0, 50, team))
    with pytest.raises(InvalidInputError):
        solve(pool)


def test_solver_raises_when_team_cap_unsatisfiable():
    # All 22 candidates on the same team → can't pick 11 without >7 from one team.
    pool = [
        _candidate(f"P{i}", "BAT" if i < 6 else ("BOWL" if i < 14 else ("ALL" if i < 18 else "WK-BAT")), 8.0, 50, "OnlyTeam")
        for i in range(22)
    ]
    with pytest.raises(InvalidInputError):
        solve(pool)


def test_solver_rejects_unknown_strategy():
    with pytest.raises(InvalidInputError):
        solve(_synthetic_pool(), strategy="moonshot")
