"""Registers the static-data MCP resources (JSON text).

Reference data a client can read once instead of probing tools: the WC 2026
draw, football team codes, F1 circuit profiles, cricket venues, IPL team codes
and the Dream11 scoring profile. Each reads the same seed file or module the
tools use, so there is one source of truth.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from mcp.server.fastmcp import FastMCP


def _json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _buckets(buckets: tuple[tuple[float, float, int], ...]) -> list[list]:
    # Strict JSON has no Infinity: an open bound is null.
    def bound(x: float) -> float | None:
        return None if abs(x) == float("inf") else x

    return [[bound(lo), bound(hi), pts] for lo, hi, pts in buckets]


def _wc2026_draw() -> dict:
    from sportiq.football.adapters.static_seed import load_wc2026

    wc = load_wc2026()
    return {"format": wc.get("format", {}), "groups": wc.get("groups", {})}


def _football_team_codes() -> dict:
    from sportiq.football.adapters.static_seed import load_wc2026
    from sportiq.football.models.results_state import _NAME_ALIASES

    aliases: dict[str, list[str]] = {}
    for alias, code in _NAME_ALIASES.items():
        aliases.setdefault(code, []).append(alias)
    return {
        "teams": {
            code: {"name": meta.get("name", code), "aliases": sorted(aliases.get(code, []))}
            for code, meta in load_wc2026().get("teams", {}).items()
        }
    }


def _f1_circuits() -> dict:
    from sportiq.f1.circuits import load_circuit_profiles

    return {"circuits": load_circuit_profiles()}


def _cricket_venues() -> dict:
    from sportiq.cricket.adapters.static_seed import _load

    venues = _load("venues.json") or {}
    return {
        "venues": {
            key: {"name": rec.get("name", key), "city": rec.get("city")}
            for key, rec in venues.items()
        }
    }


def _cricket_teams() -> dict:
    from sportiq.cricket.teams import IPL_TEAM_NAMES

    return {"teams": dict(IPL_TEAM_NAMES)}


def _cricket_scoring_profile() -> dict:
    from sportiq.cricket.data.scoring import (
        ECONOMY_BUCKETS,
        SCORING,
        SCORING_PROFILE,
        SR_BUCKETS,
    )

    return {
        "profile": SCORING_PROFILE,
        "points": asdict(SCORING),
        "strike_rate_buckets": _buckets(SR_BUCKETS),
        "economy_buckets": _buckets(ECONOMY_BUCKETS),
    }


def register_static_resources(mcp: FastMCP) -> None:
    @mcp.resource(
        "sportiq://football/wc2026/draw",
        name="football-wc2026-draw",
        title="FIFA World Cup 2026 draw",
        description="WC 2026 format and the 12 groups of team codes.",
        mime_type="application/json",
    )
    def get_wc2026_draw() -> str:
        """Return the WC 2026 draw (format + groups)."""
        return _json(_wc2026_draw())

    @mcp.resource(
        "sportiq://football/team-codes",
        name="football-team-codes",
        title="Football team codes",
        description="WC 2026 team code → name and accepted name aliases.",
        mime_type="application/json",
    )
    def get_football_team_codes() -> str:
        """Return WC 2026 team codes with names and aliases."""
        return _json(_football_team_codes())

    @mcp.resource(
        "sportiq://f1/circuits",
        name="f1-circuits",
        title="F1 circuit profiles",
        description="Measured circuit profiles (pit loss, lap length) keyed by circuit key.",
        mime_type="application/json",
    )
    def get_f1_circuits() -> str:
        """Return the bundled F1 circuit profiles."""
        return _json(_f1_circuits())

    @mcp.resource(
        "sportiq://cricket/venues",
        name="cricket-venues",
        title="Cricket venues",
        description="Venue keys accepted by the cricket tools, with names and cities.",
        mime_type="application/json",
    )
    def get_cricket_venues() -> str:
        """Return the bundled cricket venue keys and names."""
        return _json(_cricket_venues())

    @mcp.resource(
        "sportiq://cricket/teams",
        name="cricket-teams",
        title="IPL team codes",
        description="IPL franchise code → official name.",
        mime_type="application/json",
    )
    def get_cricket_teams() -> str:
        """Return IPL team codes and names."""
        return _json(_cricket_teams())

    @mcp.resource(
        "sportiq://cricket/scoring-profile",
        name="cricket-scoring-profile",
        title="Dream11 T20 scoring profile",
        description="The versioned Dream11 T20 points table the fantasy tools score with.",
        mime_type="application/json",
    )
    def get_cricket_scoring_profile() -> str:
        """Return the Dream11 T20 scoring profile id and constants."""
        return _json(_cricket_scoring_profile())
