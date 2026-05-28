"""Tests for match_resolver.resolve_match()."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sportiq.core.errors import NotFoundError
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

    scorecard_val = {"data": {"teamInfo": [{"name": "IND"}, {"name": "AUS"}], "venue": "eden_gardens"}}
    with (
        patch("sportiq.cricket.match_resolver.fixtures_chain") as mock_f,
        patch("sportiq.cricket.match_resolver.scorecard_chain") as mock_s,
    ):
        mock_f.fetch = AsyncMock(side_effect=Exception("fixtures failed"))
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
        mock_f.fetch = AsyncMock(side_effect=Exception("failed"))
        mock_s.fetch = AsyncMock(side_effect=Exception("failed"))
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
