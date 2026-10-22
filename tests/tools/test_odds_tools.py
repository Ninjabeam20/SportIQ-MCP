"""End-to-end odds tool tests — chain output stubbed, envelope shape asserted."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.fallback import FallbackResult

_EVENTS = {
    "events": [
        {
            "event_id": "e1",
            "home": "Mumbai Indians",
            "away": "Chennai Super Kings",
            "commence_time": "2026-04-12T14:00:00Z",
            "bookmakers": [],
        },
        {
            "event_id": "e2",
            "home": "Royal Challengers Bengaluru",
            "away": "Kolkata Knight Riders",
            "commence_time": "2026-04-13T10:00:00Z",
            "bookmakers": [],
        },
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


async def test_cricket_odds_team_filter_keeps_sibling_keys():
    from sportiq.cricket import tools

    payload = {
        "events": list(_EVENTS["events"]),
        "fetched_at": "2026-08-13T00:00:00Z",
    }
    with patch("sportiq.cricket.tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_ok(payload))
        response = await tools.cricket_get_live_odds(team="mumbai")

    assert len(response["data"]["events"]) == 1
    assert response["data"]["fetched_at"] == "2026-08-13T00:00:00Z"


async def test_cricket_odds_missing_key_returns_all_sources_failed():
    from sportiq.cricket import tools

    err = AllSourcesFailedError(
        "no key",
        attempts=[{"name": "theodds", "status": "error", "error": "MissingCredentialsError"}],
    )
    with patch("sportiq.cricket.tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=err)
        response = await tools.cricket_get_live_odds()

    assert response["error"]["code"] == "ALL_SOURCES_FAILED"


# -- football_get_odds --------------------------------------------------------


async def test_football_odds_success_returns_all_events():
    from sportiq.football import tools

    payload = {
        "events": [
            {
                "event_id": "f1",
                "home": "Argentina",
                "away": "Mexico",
                "commence_time": "2026-06-11T19:00:00Z",
                "bookmakers": [],
            },
        ]
    }
    with patch("sportiq.football.tools.football_odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_ok(payload))
        response = await tools.football_get_odds()

    assert response["data"]["events"][0]["home"] == "Argentina"


async def test_football_odds_team_filter():
    from sportiq.football import tools

    payload = {
        "events": [
            {
                "event_id": "f1",
                "home": "Argentina",
                "away": "Mexico",
                "commence_time": "",
                "bookmakers": [],
            },
            {
                "event_id": "f2",
                "home": "Brazil",
                "away": "Croatia",
                "commence_time": "",
                "bookmakers": [],
            },
        ]
    }
    with patch("sportiq.football.tools.football_odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_ok(payload))
        response = await tools.football_get_odds(team="brazil")

    assert len(response["data"]["events"]) == 1
    assert response["data"]["events"][0]["away"] == "Croatia"


async def test_football_odds_team_filter_keeps_sibling_keys():
    from sportiq.football import tools

    payload = {
        "events": [
            {
                "event_id": "f1",
                "home": "Argentina",
                "away": "Mexico",
                "commence_time": "",
                "bookmakers": [],
            },
            {
                "event_id": "f2",
                "home": "Brazil",
                "away": "Croatia",
                "commence_time": "",
                "bookmakers": [],
            },
        ],
        "fetched_at": "2026-08-13T00:00:00Z",
    }
    with patch("sportiq.football.tools.football_odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_ok(payload))
        response = await tools.football_get_odds(team="brazil")

    assert len(response["data"]["events"]) == 1
    assert response["data"]["fetched_at"] == "2026-08-13T00:00:00Z"


async def test_football_odds_missing_key_returns_all_sources_failed():
    from sportiq.football import tools

    err = AllSourcesFailedError("no key", attempts=[{"name": "theodds", "status": "error"}])
    with patch("sportiq.football.tools.football_odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=err)
        response = await tools.football_get_odds()

    assert response["error"]["code"] == "ALL_SOURCES_FAILED"


# -- value-bet paths tolerate a null team name (P1-13) --------------------------


async def test_football_find_value_bets_skips_event_with_null_team_name():
    from sportiq.football import intel_tools
    from sportiq.football.adapters.static_seed import load_elo_seed, load_wc2026

    wc = load_wc2026()
    draw = {"groups": wc["groups"], "teams": wc["teams"], "ratings": load_elo_seed()}
    book = [{"name": "TestBook", "home": 2.0, "draw": 3.4, "away": 3.8}]
    events = {
        "events": [
            {"event_id": "bad", "home": None, "away": "Spain", "bookmakers": book},
            {"event_id": "ok", "home": "Spain", "away": "Argentina", "bookmakers": book},
        ]
    }
    with (
        patch("sportiq.football.intel_tools.football_odds_chain") as mock_odds,
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
    ):
        mock_odds.fetch = AsyncMock(return_value=_ok(events))
        mock_groups.fetch = AsyncMock(return_value=_ok(draw, source="static_seed"))
        result = await intel_tools.football_find_value_bets(team="spain")

    assert "data" in result and "meta" in result
    assert result["data"]["events_analysed"] == 1


async def test_cricket_find_value_bets_tolerates_null_team_name():
    from sportiq.cricket import intel_tools

    events = {
        "events": [
            {"event_id": "bad", "home": None, "away": "Mumbai Indians", "bookmakers": []},
            {
                "event_id": "ok",
                "home": "Mumbai Indians",
                "away": "Delhi Capitals",
                "bookmakers": [],
            },
        ]
    }
    with patch("sportiq.cricket.intel_tools.odds_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_ok(events))
        result = await intel_tools.cricket_find_value_bets(team="mumbai")

    assert "data" in result and "meta" in result
    assert result["data"]["events_analysed"] == 1
