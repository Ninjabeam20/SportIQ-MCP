"""The Odds API adapter tests (cricket + football) — all HTTP mocked with respx."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from sportiq.config import settings

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "theodds"
_BASE = "https://api.the-odds-api.com/v4"


def _load(name: str) -> list:
    return json.loads((_FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def _with_key(monkeypatch):
    monkeypatch.setattr(settings, "theodds_key", "test-key")


@respx.mock
async def test_cricket_adapter_normalises_events():
    from sportiq.cricket.adapters.theodds import TheOddsCricketAdapter

    respx.get(f"{_BASE}/sports/cricket_ipl/odds").mock(
        return_value=Response(200, json=_load("cricket_ipl.json"))
    )
    result = await TheOddsCricketAdapter().fetch()
    events = result["events"]
    assert events[0]["home"] == "Mumbai Indians"
    assert events[0]["away"] == "Chennai Super Kings"
    assert events[0]["bookmakers"][0] == {"name": "Betfair", "home": 1.85, "away": 2.05}


@respx.mock
async def test_football_adapter_normalises_events_ignores_draw():
    from sportiq.football.adapters.theodds import TheOddsFootballAdapter

    respx.get(f"{_BASE}/sports/soccer_fifa_world_cup/odds").mock(
        return_value=Response(200, json=_load("soccer_wc.json"))
    )
    result = await TheOddsFootballAdapter().fetch()
    events = result["events"]
    assert events[0]["home"] == "Argentina"
    # h2h reduced to home/away decimal prices; the Draw outcome is dropped.
    assert events[0]["bookmakers"][0] == {"name": "Pinnacle", "home": 1.65, "away": 5.20}


@respx.mock
async def test_cricket_adapter_skips_bookmaker_without_h2h():
    from sportiq.cricket.adapters.theodds import TheOddsCricketAdapter

    payload = [
        {
            "id": "x",
            "home_team": "A",
            "away_team": "B",
            "commence_time": "2026-04-12T14:00:00Z",
            "bookmakers": [
                {"title": "NoMarkets", "markets": [{"key": "totals", "outcomes": []}]}
            ],
        }
    ]
    respx.get(f"{_BASE}/sports/cricket_ipl/odds").mock(return_value=Response(200, json=payload))
    result = await TheOddsCricketAdapter().fetch()
    assert result["events"][0]["bookmakers"] == []


async def test_cricket_missing_key_raises_missing_credentials(monkeypatch):
    from sportiq.core.errors import MissingCredentialsError
    from sportiq.cricket.adapters.theodds import TheOddsCricketAdapter

    monkeypatch.setattr(settings, "theodds_key", None)
    with pytest.raises(MissingCredentialsError):
        await TheOddsCricketAdapter().fetch()


async def test_football_missing_key_raises_missing_credentials(monkeypatch):
    from sportiq.core.errors import MissingCredentialsError
    from sportiq.football.adapters.theodds import TheOddsFootballAdapter

    monkeypatch.setattr(settings, "theodds_key", None)
    with pytest.raises(MissingCredentialsError):
        await TheOddsFootballAdapter().fetch()


async def test_healthcheck_false_without_key(monkeypatch):
    from sportiq.cricket.adapters.theodds import TheOddsCricketAdapter

    monkeypatch.setattr(settings, "theodds_key", None)
    assert await TheOddsCricketAdapter().healthcheck() is False
