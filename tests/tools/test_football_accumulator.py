"""Tool-layer tests for football_build_accumulator — value_bets stubbed, envelope asserted."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from sportiq.football.intel_tools import football_build_accumulator


def _value_bet(event_id: str, outcome: str, edge: float, model_prob: float, market_odds: float) -> dict:
    return {
        "event_id": event_id,
        "home": "TeamA",
        "away": "TeamB",
        "outcome": outcome,
        "model_prob": model_prob,
        "fair_odds": round(1.0 / model_prob, 3),
        "market_odds": market_odds,
        "edge": edge,
        "bookmaker": "betfair",
    }


def _value_bets_response(bets: list[dict]) -> dict:
    return {
        "data": {"value_bets": bets, "min_edge": 0.05, "events_analysed": len(bets)},
        "meta": {"source": "theodds", "estimated": True, "is_stale": False, "data_age_seconds": 0, "fallback_used": False, "duration_ms": 5},
    }


# -- INVALID_INPUT -------------------------------------------------------------


async def test_invalid_legs_too_few():
    """legs=1 → INVALID_INPUT."""
    result = await football_build_accumulator(legs=1)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_invalid_legs_too_many():
    """legs=9 → INVALID_INPUT."""
    result = await football_build_accumulator(legs=9)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_invalid_min_edge():
    """min_edge=0 → INVALID_INPUT."""
    result = await football_build_accumulator(min_edge=0)
    assert result["error"]["code"] == "INVALID_INPUT"


# -- ALL_SOURCES_FAILED --------------------------------------------------------


async def test_all_sources_failed():
    """football_find_value_bets returns error envelope → forward it unchanged."""
    error_resp = {"error": {"code": "ALL_SOURCES_FAILED", "message": "No odds available."}}
    with patch(
        "sportiq.football.intel_tools.football_find_value_bets",
        new=AsyncMock(return_value=error_resp),
    ):
        result = await football_build_accumulator(legs=3, min_edge=0.05)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# -- valid responses -----------------------------------------------------------


async def test_valid_returns_envelope():
    """Valid bets → data.combined_odds present, meta.estimated == True."""
    bets = [
        _value_bet("m1", "home", 0.12, 0.60, 1.9),
        _value_bet("m2", "away", 0.10, 0.50, 2.0),
        _value_bet("m3", "home", 0.08, 0.55, 1.85),
    ]
    with patch(
        "sportiq.football.intel_tools.football_find_value_bets",
        new=AsyncMock(return_value=_value_bets_response(bets)),
    ):
        result = await football_build_accumulator(legs=3, min_edge=0.05)

    assert "data" in result
    assert "meta" in result
    assert "error" not in result
    assert "combined_odds" in result["data"]
    assert result["data"]["legs_used"] == 3
    assert result["meta"]["estimated"] is True


async def test_no_value_bets_clean_response():
    """Empty value_bets list → no error, data.legs_used == 0."""
    with patch(
        "sportiq.football.intel_tools.football_find_value_bets",
        new=AsyncMock(return_value=_value_bets_response([])),
    ):
        result = await football_build_accumulator(legs=3, min_edge=0.05)

    assert "error" not in result
    assert "data" in result
    assert result["data"]["legs_used"] == 0
    assert result["meta"]["estimated"] is True
