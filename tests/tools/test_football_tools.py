"""Football tool tests — chains stubbed, envelope shape + error codes asserted."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.fallback import FallbackResult
from sportiq.football.adapters.static_seed import load_elo_seed, load_wc2026


def _fr(value, source="static_seed", is_stale=False):
    return FallbackResult(
        value=value,
        source=source,
        is_stale=is_stale,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=1,
    )


def _draw_payload() -> dict:
    wc = load_wc2026()
    return {
        "groups": wc["groups"],
        "format": wc["format"],
        "teams": wc["teams"],
        "ratings": load_elo_seed(),
        "source": "static_seed",
    }


# -- RAW tools -----------------------------------------------------------------


async def test_get_groups_returns_envelope():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await tools.football_get_groups()
    assert "data" in result and "meta" in result
    assert len(result["data"]["groups"]) == 12


async def test_get_fixtures_all_sources_failed():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_fixtures_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.football_get_fixtures()
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_get_squad_empty_team_invalid_input():
    from sportiq.football import tools

    result = await tools.football_get_squad(team="  ")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_get_match_stats_invalid_team_id():
    from sportiq.football import tools

    result = await tools.football_get_match_stats(team=0)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_get_standings_surfaces_is_stale():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_standings_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr({"standings": []}, source="cache:stale", is_stale=True))
        result = await tools.football_get_standings()
    assert result["meta"]["is_stale"] is True


# -- INTEL tools ---------------------------------------------------------------


async def test_xg_model_returns_probabilities():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_xg_model(home_team="ARG", away_team="USA")
    data = result["data"]
    assert abs(data["home_win"] + data["draw"] + data["away_win"] - 1.0) < 1e-6
    assert result["meta"]["estimated"] is True
    assert "is_stale" in result["meta"]


async def test_xg_model_unknown_team_not_found():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_xg_model(home_team="ZZZ", away_team="ARG")
    assert result["error"]["code"] == "NOT_FOUND"


async def test_match_predictor_returns_scoreline():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_match_predictor(home_team="BRA", away_team="QAT")
    assert "-" in result["data"]["most_likely_score"]
    assert result["data"]["predicted_winner"] in {"BRA", "QAT", "DRAW"}


async def test_simulate_group_advance_mass_two():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_simulate_group(group="A", iterations=1500)
    total = sum(t["p_advance"] for t in result["data"]["teams"].values())
    assert abs(total - 2.0) < 0.01  # exactly 2 advance/iter; tol covers 4dp rounding


async def test_simulate_group_unknown_group_not_found():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_simulate_group(group="Z")
    assert result["error"]["code"] == "NOT_FOUND"


async def test_simulate_bracket_flagship_invariants():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_simulate_bracket(iterations=1500, seed=1)
    data = result["data"]
    assert data["iterations"] == 1500
    assert abs(sum(t["reach_r32"] for t in data["teams"].values()) - 32.0) < 0.01
    assert data["champion"] in data["teams"]
    assert result["meta"]["estimated"] is True


async def test_knockout_path_returns_team_row():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_knockout_path(team="FRA", iterations=1200, seed=1)
    assert result["data"]["team"] == "FRA"
    assert 0.0 <= result["data"]["win"] <= 1.0
