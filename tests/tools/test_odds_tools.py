"""End-to-end odds tool tests — chain output stubbed, envelope shape asserted."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.fallback import FallbackResult

_EVENTS = {
    "events": [
        {"event_id": "e1", "home": "Mumbai Indians", "away": "Chennai Super Kings",
         "commence_time": "2026-04-12T14:00:00Z", "bookmakers": []},
        {"event_id": "e2", "home": "Royal Challengers Bengaluru", "away": "Kolkata Knight Riders",
         "commence_time": "2026-04-13T10:00:00Z", "bookmakers": []},
    ]
}


def _ok(payload: dict, source: str = "theodds") -> FallbackResult:
    return FallbackResult(value=payload, source=source, data_age_seconds=12, duration_ms=30)


# -- cricket_get_live_odds ----------------------------------------------------

async def test_cricket_odds_success_returns_all_events():
    from sportiq.cricket import tools

    with patch("sportiq.cricket.tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_ok(dict(_EVENTS)))
        response = await tools.cricket_get_live_odds()

    assert len(response["data"]["events"]) == 2
    assert response["meta"]["source"] == "theodds"


async def test_cricket_odds_team_filter_matches_substring():
    from sportiq.cricket import tools

    with patch("sportiq.cricket.tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_ok({"events": list(_EVENTS["events"])}))
        response = await tools.cricket_get_live_odds(team="mumbai")

    assert len(response["data"]["events"]) == 1
    assert response["data"]["events"][0]["home"] == "Mumbai Indians"


async def test_cricket_odds_missing_key_returns_all_sources_failed():
    from sportiq.cricket import tools

    err = AllSourcesFailedError(
        "no key", attempts=[{"name": "theodds", "status": "error", "error": "MissingCredentialsError"}]
    )
    with patch("sportiq.cricket.tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=err)
        response = await tools.cricket_get_live_odds()

    assert response["error"]["code"] == "ALL_SOURCES_FAILED"


# -- football_get_odds --------------------------------------------------------

async def test_football_odds_success_returns_all_events():
    from sportiq.football import tools

    payload = {"events": [
        {"event_id": "f1", "home": "Argentina", "away": "Mexico",
         "commence_time": "2026-06-11T19:00:00Z", "bookmakers": []},
    ]}
    with patch("sportiq.football.tools.football_odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_ok(payload))
        response = await tools.football_get_odds()

    assert response["data"]["events"][0]["home"] == "Argentina"


async def test_football_odds_team_filter():
    from sportiq.football import tools

    payload = {"events": [
        {"event_id": "f1", "home": "Argentina", "away": "Mexico", "commence_time": "", "bookmakers": []},
        {"event_id": "f2", "home": "Brazil", "away": "Croatia", "commence_time": "", "bookmakers": []},
    ]}
    with patch("sportiq.football.tools.football_odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_ok(payload))
        response = await tools.football_get_odds(team="brazil")

    assert len(response["data"]["events"]) == 1
    assert response["data"]["events"][0]["away"] == "Croatia"


async def test_football_odds_missing_key_returns_all_sources_failed():
    from sportiq.football import tools

    err = AllSourcesFailedError("no key", attempts=[{"name": "theodds", "status": "error"}])
    with patch("sportiq.football.tools.football_odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=err)
        response = await tools.football_get_odds()

    assert response["error"]["code"] == "ALL_SOURCES_FAILED"
