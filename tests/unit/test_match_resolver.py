"""Tests for match_resolver.resolve_match()."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.core.fallback import FallbackResult


def _fr(value):
    return FallbackResult(
        value=value,
        source="cricapi",
        is_stale=False,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=1,
    )


async def test_resolve_match_from_fixtures():
    from sportiq.cricket import match_resolver

    fixtures_val = {"data": [{"id": "m123", "teams": ["MI", "CSK"], "venue": "wankhede"}]}
    with patch("sportiq.cricket.match_resolver.fixtures_chain") as mock_f:
        mock_f.fetch = AsyncMock(return_value=_fr(fixtures_val))
        result = await match_resolver.resolve_match("m123")

    assert result["team_a"] == "MI"
    assert result["team_b"] == "CSK"
    assert result["venue"] == "wankhede"


async def test_resolve_match_falls_back_to_scorecard():
    from sportiq.cricket import match_resolver

    scorecard_val = {
        "data": {"teamInfo": [{"name": "IND"}, {"name": "AUS"}], "venue": "eden_gardens"}
    }
    with (
        patch("sportiq.cricket.match_resolver.fixtures_chain") as mock_f,
        patch("sportiq.cricket.match_resolver.scorecard_chain") as mock_s,
    ):
        mock_f.fetch = AsyncMock(side_effect=AllSourcesFailedError("fixtures failed"))
        mock_s.fetch = AsyncMock(return_value=_fr(scorecard_val))
        result = await match_resolver.resolve_match("m456")

    assert result["team_a"] == "IND"
    assert result["team_b"] == "AUS"


async def test_resolve_match_raises_not_found_when_no_data():
    from sportiq.cricket import match_resolver

    with (
        patch("sportiq.cricket.match_resolver.fixtures_chain") as mock_f,
        patch("sportiq.cricket.match_resolver.scorecard_chain") as mock_s,
    ):
        mock_f.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed"))
        mock_s.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed"))
        with pytest.raises(NotFoundError):
            await match_resolver.resolve_match("nonexistent")


async def test_resolve_match_uses_match_id_from_fixtures():
    from sportiq.cricket import match_resolver

    # Multiple matches — should only match the right one
    fixtures_val = {
        "data": [
            {"id": "m001", "teams": ["RCB", "KKR"], "venue": "chinnaswamy"},
            {"id": "m002", "teams": ["MI", "CSK"], "venue": "wankhede"},
        ]
    }
    with patch("sportiq.cricket.match_resolver.fixtures_chain") as mock_f:
        mock_f.fetch = AsyncMock(return_value=_fr(fixtures_val))
        result = await match_resolver.resolve_match("m002")

    assert result["team_a"] == "MI"
    assert result["team_b"] == "CSK"


@pytest.mark.parametrize("source", ["fixtures", "scorecard"])
async def test_resolve_match_reraises_unexpected_chain_failure(source):
    from sportiq.cricket import match_resolver

    with (
        patch("sportiq.cricket.match_resolver.fixtures_chain") as mock_f,
        patch("sportiq.cricket.match_resolver.scorecard_chain") as mock_s,
    ):
        fixtures_error = (
            RuntimeError("unexpected fixtures bug")
            if source == "fixtures"
            else AllSourcesFailedError("fixtures unavailable")
        )
        mock_f.fetch = AsyncMock(side_effect=fixtures_error)
        mock_s.fetch = AsyncMock(side_effect=RuntimeError("unexpected scorecard bug"))
        with pytest.raises(RuntimeError, match=f"unexpected {source} bug"):
            await match_resolver.resolve_match("m123")


async def test_resolve_match_returns_series_id_from_fixtures():
    # opus cook8 T8.2: CricAPI match objects carry series_id; the squad chain needs it.
    from sportiq.cricket import match_resolver

    fixtures_val = {
        "matches": [{"id": "m7", "teams": ["MI", "CSK"], "venue": "Wankhede", "series_id": "s2026"}]
    }
    with patch("sportiq.cricket.match_resolver.fixtures_chain") as mock_f:
        mock_f.fetch = AsyncMock(return_value=_fr(fixtures_val))
        result = await match_resolver.resolve_match("m7")

    assert result["series_id"] == "s2026"


async def test_resolve_match_series_id_none_when_absent():
    from sportiq.cricket import match_resolver

    fixtures_val = {"data": [{"id": "m123", "teams": ["MI", "CSK"], "venue": "wankhede"}]}
    with patch("sportiq.cricket.match_resolver.fixtures_chain") as mock_f:
        mock_f.fetch = AsyncMock(return_value=_fr(fixtures_val))
        result = await match_resolver.resolve_match("m123")

    assert result["series_id"] is None


async def test_resolve_match_maps_rapidapi_match_info_shape():
    # opus cook8 T8.9: RapidAPI Cricbuzz matchInfo (matchId, team1.teamName, venueInfo.ground).
    from sportiq.cricket import match_resolver

    fixtures_val = {
        "matches": [
            {
                "matchId": 99001,
                "seriesId": 9237,
                "team1": {"teamName": "India", "teamSName": "IND"},
                "team2": {"teamName": "Australia", "teamSName": "AUS"},
                "venueInfo": {"ground": "MCG", "city": "Melbourne"},
            }
        ]
    }
    with patch("sportiq.cricket.match_resolver.fixtures_chain") as mock_f:
        mock_f.fetch = AsyncMock(return_value=_fr(fixtures_val))
        result = await match_resolver.resolve_match("99001")

    assert result == {
        "team_a": "India",
        "team_b": "Australia",
        "venue": "MCG",
        "series_id": "9237",
    }
