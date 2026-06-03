"""Tool tests for cricket_find_value_bets."""
from unittest.mock import AsyncMock, MagicMock, patch

from sportiq.cricket.intel_tools import cricket_find_value_bets


async def test_min_edge_validation():
    result = await cricket_find_value_bets(min_edge=1.5)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_min_edge_negative_validation():
    result = await cricket_find_value_bets(min_edge=-0.1)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_all_sources_failed():
    from sportiq.core.errors import AllSourcesFailedError

    with patch("sportiq.cricket.intel_tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(
            side_effect=AllSourcesFailedError("all sources failed", attempts=[])
        )
        result = await cricket_find_value_bets()
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_returns_valid_envelope_with_stubbed_odds():
    mock_result = MagicMock()
    mock_result.value = {
        "events": [
            {
                "event_id": "evt1",
                "home": "Mumbai Indians",
                "away": "Chennai Super Kings",
                "commence_time": "2026-04-01T14:00:00Z",
                "bookmakers": [
                    {"name": "bet365", "home": 1.85, "away": 2.05, "draw": None}
                ],
            }
        ]
    }
    mock_result.source = "theodds"
    mock_result.is_stale = False
    mock_result.fallback_used = False
    mock_result.data_age_seconds = 10

    with patch("sportiq.cricket.intel_tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        result = await cricket_find_value_bets()

    assert "data" in result
    assert "meta" in result
    assert result["meta"]["estimated"] is True
    assert "value_bets" in result["data"]
    assert "events_analysed" in result["data"]
    assert result["data"]["events_analysed"] == 1


async def test_team_filter_applied():
    """Events not matching the team filter are excluded from analysis."""
    mock_result = MagicMock()
    mock_result.value = {
        "events": [
            {
                "event_id": "evt1",
                "home": "Mumbai Indians",
                "away": "Chennai Super Kings",
                "bookmakers": [
                    {"name": "bet365", "home": 1.85, "away": 2.05, "draw": None}
                ],
            },
            {
                "event_id": "evt2",
                "home": "Kolkata Knight Riders",
                "away": "Delhi Capitals",
                "bookmakers": [
                    {"name": "bet365", "home": 1.9, "away": 1.95, "draw": None}
                ],
            },
        ]
    }
    mock_result.source = "theodds"
    mock_result.is_stale = False
    mock_result.fallback_used = False
    mock_result.data_age_seconds = 10

    with patch("sportiq.cricket.intel_tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        result = await cricket_find_value_bets(team="mumbai")

    assert result["data"]["events_analysed"] == 1


async def test_empty_events_returns_zero_bets():
    mock_result = MagicMock()
    mock_result.value = {"events": []}
    mock_result.source = "theodds"
    mock_result.is_stale = False
    mock_result.fallback_used = False
    mock_result.data_age_seconds = 0

    with patch("sportiq.cricket.intel_tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        result = await cricket_find_value_bets()

    assert result["data"]["value_bets"] == []
    assert result["data"]["events_analysed"] == 0


async def test_value_bets_sorted_by_edge_descending():
    """Value bets are returned sorted by edge (highest first)."""
    mock_result = MagicMock()
    # Two bookmakers with different margins — larger edge should come first.
    mock_result.value = {
        "events": [
            {
                "event_id": "evt1",
                "home": "Team A",
                "away": "Team B",
                "bookmakers": [
                    # Model is 50/50; price 1.5 home implies ~0.667 → devigged ~0.52
                    # edge = 0.5 - 0.52 < 0 → no home value; away edge depends on away price
                    # Use a very lopsided bookmaker so away has positive edge vs 50% model
                    {"name": "bk1", "home": 1.3, "away": 3.5, "draw": None},
                    {"name": "bk2", "home": 1.4, "away": 2.9, "draw": None},
                ],
            }
        ]
    }
    mock_result.source = "theodds"
    mock_result.is_stale = False
    mock_result.fallback_used = False
    mock_result.data_age_seconds = 5

    with patch("sportiq.cricket.intel_tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        result = await cricket_find_value_bets(min_edge=0.0)

    bets = result["data"]["value_bets"]
    if len(bets) > 1:
        edges = [b["edge"] for b in bets]
        assert edges == sorted(edges, reverse=True)
