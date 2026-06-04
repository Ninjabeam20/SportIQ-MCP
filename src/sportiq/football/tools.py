"""Football RAW tools — Phase 4.

Thin wrappers: validate args -> call chain.fetch() -> return tool_response.
"""
from __future__ import annotations

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.tool_response import Envelope, error_envelope, paginate, tool_response
from sportiq.football.chains import (
    football_fixtures_chain,
    football_groups_chain,
    football_odds_chain,
    football_scorers_chain,
    football_squad_chain,
    football_standings_chain,
    football_team_stats_chain,
)


def _filter_events_by_team(events: list[dict], team: str) -> list[dict]:
    """Case-insensitive substring match against both sides of each event."""
    q = team.strip().lower()
    return [
        e
        for e in events
        if q in (e.get("home") or "").lower() or q in (e.get("away") or "").lower()
    ]


async def football_get_groups() -> Envelope:
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


async def football_get_fixtures(limit: int = 50, offset: int = 0) -> Envelope:
    """Return World Cup 2026 fixtures (live providers, else the group schedule).

    Args:
        limit: Max fixtures to return, 1..200 (default 50).
        offset: Number of fixtures to skip for paging (default 0).

    Returns:
        data.fixtures: page of {home, away, date/group, status, home_goals, away_goals}.
        data.pagination: {total, count, offset, limit, has_more, next_offset}.
        meta.source: adapter that served the data (static_seed = group schedule only).
    """
    if not 1 <= limit <= 200:
        return error_envelope(code="INVALID_INPUT", message="limit must be in [1, 200].")
    if offset < 0:
        return error_envelope(code="INVALID_INPUT", message="offset must be >= 0.")
    try:
        result = await football_fixtures_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch World Cup 2026 fixtures.",
            sources_tried=e.attempts,
        )
    result.value = paginate(result.value, "fixtures", limit, offset)
    return tool_response(result)


async def football_get_standings(limit: int = 50, offset: int = 0) -> Envelope:
    """Return current World Cup 2026 group standings.

    Args:
        limit: Max standing rows to return, 1..200 (default 50).
        offset: Number of rows to skip for paging (default 0).

    Returns:
        data.standings: page of {rank, team, group, points, played, goals_diff}.
        data.pagination: {total, count, offset, limit, has_more, next_offset}.
        meta.source: adapter that served the data.
    """
    if not 1 <= limit <= 200:
        return error_envelope(code="INVALID_INPUT", message="limit must be in [1, 200].")
    if offset < 0:
        return error_envelope(code="INVALID_INPUT", message="offset must be >= 0.")
    try:
        result = await football_standings_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch World Cup 2026 standings.",
            sources_tried=e.attempts,
        )
    result.value = paginate(result.value, "standings", limit, offset)
    return tool_response(result)


async def football_get_squad(team: str) -> Envelope:
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
    if len(team) > 100:
        return error_envelope(code="INVALID_INPUT", message="team must not exceed 100 characters.")
    try:
        result = await football_squad_chain.fetch(team=team.strip())
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch squad for {team!r}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def football_get_match_stats(team: int) -> Envelope:
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


async def football_get_top_scorers() -> Envelope:
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


async def football_get_odds(team: str | None = None) -> Envelope:
    """Return live bookmaker head-to-head odds for upcoming World Cup 2026 matches.

    Sourced from The Odds API (requires THEODDS_KEY). Without a key the call
    returns a clean ALL_SOURCES_FAILED envelope rather than crashing.

    Args:
        team: Optional team name to filter events (case-insensitive substring,
            matched against both sides). Omit to return every WC event.

    Returns:
        data.events: list of {event_id, home, away, commence_time, bookmakers:
            [{name, home, draw, away}]} with decimal 1X2 prices per bookmaker.
        meta.source: adapter that served the data (theodds / cache:stale).
    """
    try:
        result = await football_odds_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="No football odds source is available right now.",
            sources_tried=e.attempts,
            suggestion="Set THEODDS_KEY to enable live odds.",
        )
    if team and team.strip():
        result.value = {"events": _filter_events_by_team(result.value["events"], team)}
    return tool_response(result)


def register_football_tools(mcp) -> None:
    """Register all football tools on the supplied FastMCP instance."""
    from sportiq.core.tool_meta import READ_ONLY
    from sportiq.football.intel_tools import register_football_intel_tools

    mcp.tool(annotations=READ_ONLY)(football_get_groups)
    mcp.tool(annotations=READ_ONLY)(football_get_fixtures)
    mcp.tool(annotations=READ_ONLY)(football_get_standings)
    mcp.tool(annotations=READ_ONLY)(football_get_squad)
    mcp.tool(annotations=READ_ONLY)(football_get_match_stats)
    mcp.tool(annotations=READ_ONLY)(football_get_top_scorers)
    mcp.tool(annotations=READ_ONLY)(football_get_odds)
    register_football_intel_tools(mcp)
