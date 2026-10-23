"""Static-data MCP resources register and return strict, parseable JSON."""

from __future__ import annotations

import asyncio
import json

import pytest

from sportiq import server

_EXPECTED: dict[str, set[str]] = {
    "sportiq://football/wc2026/draw": {"format", "groups"},
    "sportiq://football/team-codes": {"teams"},
    "sportiq://f1/circuits": {"circuits"},
    "sportiq://cricket/venues": {"venues"},
    "sportiq://cricket/teams": {"teams"},
    "sportiq://cricket/scoring-profile": {
        "profile",
        "points",
        "strike_rate_buckets",
        "economy_buckets",
    },
}


def _reject_constant(name: str) -> None:
    raise ValueError(f"non-strict JSON constant {name}")


def test_resources_list_includes_static_resources_and_instructions():
    uris = {str(r.uri) for r in asyncio.run(server.mcp.list_resources())}
    assert set(_EXPECTED) | {"sportiq://instructions"} <= uris


@pytest.mark.parametrize("uri", sorted(_EXPECTED))
def test_resource_returns_strict_json_with_expected_keys(uri: str):
    contents = list(asyncio.run(server.mcp.read_resource(uri)))
    assert contents[0].mime_type == "application/json"
    payload = json.loads(contents[0].content, parse_constant=_reject_constant)
    assert set(payload) == _EXPECTED[uri]


def test_scoring_profile_resource_matches_scoring_module():
    from sportiq.cricket.data.scoring import SCORING, SCORING_PROFILE

    contents = list(asyncio.run(server.mcp.read_resource("sportiq://cricket/scoring-profile")))
    payload = json.loads(contents[0].content)
    assert payload["profile"] == SCORING_PROFILE
    assert payload["points"]["wicket"] == SCORING.wicket


def test_cricket_teams_resource_lists_ipl_codes():
    contents = list(asyncio.run(server.mcp.read_resource("sportiq://cricket/teams")))
    teams = json.loads(contents[0].content)["teams"]
    assert teams["MI"] == "Mumbai Indians"
    assert len(teams) == 10
