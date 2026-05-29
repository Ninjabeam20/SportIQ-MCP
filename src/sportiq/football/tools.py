"""Football RAW tools — Phase 4.

Thin wrappers: validate args -> call chain.fetch() -> return tool_response.
"""
from __future__ import annotations

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.tool_response import error_envelope, tool_response
from sportiq.football.chains import (
    football_fixtures_chain,
    football_groups_chain,
    football_scorers_chain,
    football_squad_chain,
    football_standings_chain,
    football_team_stats_chain,
)


async def football_get_groups() -> dict:
    """Return the FIFA World Cup 2026 group draw and advancement format.

    Returns:
        data.groups: {group_letter: [4 team codes]} for all 12 groups.
        data.format: 48-team / 12-group / top-2 + 8-best-thirds rule.
        data.teams: team-code -> {name, fifa_code} metadata.
        meta.source: adapter that served the data.
    """
    try:
        result = await football_groups_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch World Cup 2026 group draw.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def football_get_fixtures() -> dict:
    """Return World Cup 2026 fixtures (live providers, else the group schedule).

    Returns:
        data.fixtures: list of {home, away, date/group, status, home_goals, away_goals}.
        meta.source: adapter that served the data (static_seed = group schedule only).
    """
    try:
        result = await football_fixtures_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch World Cup 2026 fixtures.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def football_get_standings() -> dict:
    """Return current World Cup 2026 group standings.

    Returns:
        data.standings: list of {rank, team, group, points, played, goals_diff}.
        meta.source: adapter that served the data.
    """
    try:
        result = await football_standings_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch World Cup 2026 standings.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def football_get_squad(team: str) -> dict:
    """Return a national team's World Cup squad.

    Args:
        team: Team code or name (e.g. "ARG"). Without an API-Football key, the
            static seed serves an empty-but-valid squad (rosters are a follow-up).

    Returns:
        data.squad: list of {name, number, position, age}.
        meta.source: adapter that served the data.
    """
    if not team or not team.strip():
        return error_envelope(code="INVALID_INPUT", message="team must be non-empty.")
    try:
        result = await football_squad_chain.fetch(team=team.strip())
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch squad for {team!r}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def football_get_match_stats(team: int) -> dict:
    """Return a team's aggregate World Cup tournament statistics.

    Network-only enrichment: requires a configured API-Football (or
    football-data.org) key. There is no offline static fallback, so without a
    key the call returns a clean ALL_SOURCES_FAILED envelope.

    Args:
        team: API-Football numeric team id (not a country code).

    Returns:
        data.team_stats: {team, played, wins, goals_for, goals_against}.
        meta.source: adapter that served the data.
    """
    if team <= 0:
        return error_envelope(code="INVALID_INPUT", message="team id must be positive.")
    try:
        result = await football_team_stats_chain.fetch(team=team)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch team stats for team {team}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def football_get_top_scorers() -> dict:
    """Return the World Cup 2026 top scorers.

    Returns:
        data.scorers: list of {name, team, goals, assists}.
        meta.source: adapter that served the data.
    """
    try:
        result = await football_scorers_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch World Cup 2026 top scorers.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


def register_football_tools(mcp) -> None:
    """Register all football tools on the supplied FastMCP instance."""
    from sportiq.football.intel_tools import register_football_intel_tools

    mcp.tool()(football_get_groups)
    mcp.tool()(football_get_fixtures)
    mcp.tool()(football_get_standings)
    mcp.tool()(football_get_squad)
    mcp.tool()(football_get_match_stats)
    mcp.tool()(football_get_top_scorers)
    register_football_intel_tools(mcp)
