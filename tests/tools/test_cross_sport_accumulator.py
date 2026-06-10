"""Tool-layer tests for cross_sport_build_accumulator — both sport sources stubbed."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from sportiq.server_tools.cross_sport import cross_sport_build_accumulator

FOOTBALL_PATCH = "sportiq.server_tools.cross_sport.football_find_value_bets"
CRICKET_PATCH = "sportiq.server_tools.cross_sport.cricket_find_value_bets"


def _value_bets_response(picks):
    return {
        "data": {"value_bets": picks, "min_edge": 0.05, "events_analysed": len(picks)},
        "meta": {"source": "test", "is_stale": False, "data_age_seconds": 0, "fallback_used": False, "duration_ms": 0, "estimated": True},
    }


def _sample_pick(event_id, edge=0.10):
    return {
        "event_id": event_id,
        "outcome": "home",
        "edge": edge,
        "model_prob": 0.60,
        "market_odds": 2.0,
        "bookmaker": "test",
    }


# -- INVALID_INPUT ----------------------------------------------------------------


async def test_invalid_legs():
    """legs=1 → INVALID_INPUT."""
    result = await cross_sport_build_accumulator(legs=1)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_invalid_min_edge():
    """min_edge=0.0 → INVALID_INPUT."""
    result = await cross_sport_build_accumulator(min_edge=0.0)
    assert result["error"]["code"] == "INVALID_INPUT"


# -- ALL_SOURCES_FAILED -----------------------------------------------------------


async def test_all_sources_failed():
    """Both sports return error envelopes → ALL_SOURCES_FAILED."""
    err = {"error": {"code": "ALL_SOURCES_FAILED", "message": "no odds"}}
    with patch(FOOTBALL_PATCH, new=AsyncMock(return_value=err)), \
         patch(CRICKET_PATCH, new=AsyncMock(return_value=err)):
        result = await cross_sport_build_accumulator(legs=3, min_edge=0.05)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# -- valid responses --------------------------------------------------------------


async def test_valid_returns_envelope():
    """Both sports return picks → combined_odds present, meta.estimated == True, both sports listed."""
    fb_picks = [_sample_pick("fb1", 0.12), _sample_pick("fb2", 0.10)]
    ck_picks = [_sample_pick("ck1", 0.09)]
    with patch(FOOTBALL_PATCH, new=AsyncMock(return_value=_value_bets_response(fb_picks))), \
         patch(CRICKET_PATCH, new=AsyncMock(return_value=_value_bets_response(ck_picks))):
        result = await cross_sport_build_accumulator(legs=3, min_edge=0.05)

    assert "data" in result
    assert "meta" in result
    assert "error" not in result
    assert "combined_odds" in result["data"]
    assert result["meta"]["estimated"] is True
    assert "football" in result["meta"]["sports_available"]
    assert "cricket" in result["meta"]["sports_available"]


async def test_sport_field_in_legs():
    """Each leg in data.legs should have a sport key."""
    fb_picks = [_sample_pick("fb1", 0.12)]
    ck_picks = [_sample_pick("ck1", 0.11)]
    with patch(FOOTBALL_PATCH, new=AsyncMock(return_value=_value_bets_response(fb_picks))), \
         patch(CRICKET_PATCH, new=AsyncMock(return_value=_value_bets_response(ck_picks))):
        result = await cross_sport_build_accumulator(legs=3, min_edge=0.05)

    assert "error" not in result
    legs = result["data"]["legs"]
    assert len(legs) > 0
    for leg in legs:
        assert "sport" in leg


async def test_staleness_from_sub_tools_is_surfaced():
    """Per fallback-contract.md, is_stale must never be swallowed: if a sport's
    odds were served from stale cache, the cross-sport meta must say so."""
    fb = _value_bets_response([_sample_pick("fb1", 0.12)])
    fb["meta"].update(
        {"is_stale": True, "data_age_seconds": 240, "fallback_used": True, "duration_ms": 35}
    )
    ck = _value_bets_response([_sample_pick("ck1", 0.11)])
    ck["meta"]["duration_ms"] = 20
    with patch(FOOTBALL_PATCH, new=AsyncMock(return_value=fb)), \
         patch(CRICKET_PATCH, new=AsyncMock(return_value=ck)):
        result = await cross_sport_build_accumulator(legs=3, min_edge=0.05)

    assert result["meta"]["is_stale"] is True
    assert result["meta"]["data_age_seconds"] == 240
    assert result["meta"]["fallback_used"] is True
    assert result["meta"]["duration_ms"] == 55


async def test_one_sport_unavailable_still_succeeds():
    """Cricket fails → only football picks used; no error envelope."""
    fb_picks = [_sample_pick("fb1", 0.12), _sample_pick("fb2", 0.10)]
    err = {"error": {"code": "ALL_SOURCES_FAILED", "message": "no odds"}}
    with patch(FOOTBALL_PATCH, new=AsyncMock(return_value=_value_bets_response(fb_picks))), \
         patch(CRICKET_PATCH, new=AsyncMock(return_value=err)):
        result = await cross_sport_build_accumulator(legs=3, min_edge=0.05)

    assert "error" not in result
    assert result["meta"]["sports_available"] == ["football"]
    assert "cricket picks unavailable" in result["meta"]["note"]
