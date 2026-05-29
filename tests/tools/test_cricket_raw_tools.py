"""End-to-end tool tests — chain output is stubbed, envelope shape is asserted."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.fallback import FallbackResult


def _ok_result(payload: dict, source: str = "cricapi") -> FallbackResult:
    return FallbackResult(
        value=payload,
        source=source,
        is_stale=False,
        data_age_seconds=5,
        fallback_used=False,
        duration_ms=42,
    )


def _stale_result(payload: dict) -> FallbackResult:
    return FallbackResult(
        value=payload,
        source="cache:stale:cricket:live_score",
        is_stale=True,
        data_age_seconds=180,
        fallback_used=True,
        duration_ms=10,
    )


# -- cricket_get_live_matches -------------------------------------------------

async def test_get_live_matches_success():
    from sportiq.cricket import tools

    mock_result = _ok_result({"matches": [{"id": "m1"}]})
    with patch("sportiq.cricket.tools.live_score_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        response = await tools.cricket_get_live_matches()

    assert "data" in response
    assert "meta" in response
    assert response["data"]["matches"][0]["id"] == "m1"
    assert response["meta"]["source"] == "cricapi"
    assert response["meta"]["is_stale"] is False


async def test_get_live_matches_stale_surfaces_in_meta():
    from sportiq.cricket import tools

    mock_result = _stale_result({"matches": [{"id": "stale_m1"}]})
    with patch("sportiq.cricket.tools.live_score_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        response = await tools.cricket_get_live_matches()

    assert response["meta"]["is_stale"] is True
    assert response["meta"]["source"].startswith("cache:stale:")


async def test_get_live_matches_all_sources_failed():
    from sportiq.cricket import tools

    err = AllSourcesFailedError("all down", attempts=[{"name": "cricapi", "status": "error", "error": "401"}])
    with patch("sportiq.cricket.tools.live_score_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=err)
        response = await tools.cricket_get_live_matches()

    assert "error" in response
    assert response["error"]["code"] == "ALL_SOURCES_FAILED"
    assert len(response["error"]["sources_tried"]) == 1


# -- cricket_get_scorecard ----------------------------------------------------

async def test_get_scorecard_success():
    from sportiq.cricket import tools

    mock_result = _ok_result({"id": "abc123", "scorecard": []})
    with patch("sportiq.cricket.tools.scorecard_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        response = await tools.cricket_get_scorecard("abc123")

    assert response["data"]["id"] == "abc123"


async def test_get_scorecard_empty_id_returns_invalid_input():
    from sportiq.cricket import tools

    response = await tools.cricket_get_scorecard("")
    assert response["error"]["code"] == "INVALID_INPUT"


# -- cricket_get_points_table -------------------------------------------------

async def test_get_points_table_success():
    from sportiq.cricket import tools

    mock_result = _ok_result({"pointsTable": [{"team": "CSK", "points": 14}]})
    with patch("sportiq.cricket.tools.standings_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        response = await tools.cricket_get_points_table("ipl2026")

    assert response["data"]["pointsTable"][0]["team"] == "CSK"


async def test_get_points_table_empty_series_id():
    from sportiq.cricket import tools

    response = await tools.cricket_get_points_table("")
    assert response["error"]["code"] == "INVALID_INPUT"


# -- cricket_get_schedule -----------------------------------------------------

async def test_get_schedule_success():
    from sportiq.cricket import tools

    mock_result = _ok_result({"matches": [{"id": "s1"}, {"id": "s2"}]})
    with patch("sportiq.cricket.tools.fixtures_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        response = await tools.cricket_get_schedule()

    assert len(response["data"]["matches"]) == 2


async def test_get_schedule_off_season_empty_list():
    from sportiq.cricket import tools

    mock_result = _ok_result({"matches": []})
    with patch("sportiq.cricket.tools.fixtures_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        response = await tools.cricket_get_schedule()

    assert response["data"]["matches"] == []
    assert "error" not in response


# -- cricket_get_squad --------------------------------------------------------

async def test_get_squad_from_static_seed():
    from sportiq.cricket import tools

    mock_result = _ok_result(
        {"players": [{"name": "Rohit Sharma"}], "team": "MI"},
        source="static_seed",
    )
    with patch("sportiq.cricket.tools.squad_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        response = await tools.cricket_get_squad("MI")

    assert response["data"]["players"][0]["name"] == "Rohit Sharma"
    assert response["meta"]["source"] == "static_seed"


async def test_get_squad_empty_team_returns_invalid_input():
    from sportiq.cricket import tools

    response = await tools.cricket_get_squad("")
    assert response["error"]["code"] == "INVALID_INPUT"


async def test_cricket_get_squad_unknown_team_returns_envelope(monkeypatch):
    """Unknown team must NOT raise: with no key the cricapi adapter is skipped
    and the static_seed terminator serves an empty-but-valid squad. Locks the
    NOT_FOUND terminator invariant against future regressions."""
    from sportiq.config import settings
    from sportiq.cricket import tools

    monkeypatch.setattr(settings, "cricapi_key", None)

    response = await tools.cricket_get_squad("Nowhere United XI")
    assert "error" not in response
    assert response["meta"]["source"] == "static_seed"
