"""Tool-layer tests for football_form_trends — chain stubbed, envelope shape asserted."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from sportiq.core.errors import AllSourcesFailedError
from sportiq.football.intel_tools import football_form_trends


def _fr(fixtures: list[dict], source: str = "static_seed", is_stale: bool = False) -> MagicMock:
    r = MagicMock()
    r.value = {"fixtures": fixtures}
    r.source = source
    r.is_stale = is_stale
    r.fallback_used = False
    r.data_age_seconds = 0
    r.duration_ms = 1
    return r


def _completed_fixture(home: str, away: str, hs: int, as_: int, date: str = "2026-01-01") -> dict:
    return {"home": home, "away": away, "home_goals": hs, "away_goals": as_, "date": date}


# -- INVALID_INPUT -------------------------------------------------------------


async def test_invalid_team_blank():
    """Blank team string → INVALID_INPUT."""
    result = await football_form_trends(team="   ")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_invalid_team_empty():
    """Empty team string → INVALID_INPUT."""
    result = await football_form_trends(team="")
    assert result["error"]["code"] == "INVALID_INPUT"


# -- ALL_SOURCES_FAILED --------------------------------------------------------


async def test_all_sources_failed():
    """Chain raises AllSourcesFailedError → ALL_SOURCES_FAILED envelope."""
    with patch("sportiq.football.intel_tools.football_fixtures_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await football_form_trends(team="Brazil")
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# -- valid responses -----------------------------------------------------------


async def test_valid_returns_envelope():
    """Chain returns fixtures → data.form_string present, meta.estimated True."""
    fixtures = [
        _completed_fixture("Brazil", "Germany", 2, 1, "2026-01-01"),
        _completed_fixture("France", "Brazil", 0, 1, "2026-01-02"),
        _completed_fixture("Brazil", "Spain", 1, 1, "2026-01-03"),
    ]
    with patch("sportiq.football.intel_tools.football_fixtures_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(fixtures))
        result = await football_form_trends(team="Brazil")

    assert "data" in result
    assert "meta" in result
    assert "form_string" in result["data"]
    assert result["data"]["matches_analysed"] == 3
    assert result["meta"]["estimated"] is True
    assert "error" not in result


async def test_off_season_no_error():
    """Chain returns empty (no completed) fixtures → matches_analysed==0, no error key."""
    fixtures = [
        {"home": "Brazil", "away": "Germany", "home_goals": None, "away_goals": None, "date": "2026-12-01"}
    ]
    with patch("sportiq.football.intel_tools.football_fixtures_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(fixtures))
        result = await football_form_trends(team="Brazil")

    assert "error" not in result
    assert result["data"]["matches_analysed"] == 0
    assert result["data"]["form_string"] == ""
    assert result["meta"]["note"] == "No completed fixtures found for this team."
    assert result["meta"]["estimated"] is True
