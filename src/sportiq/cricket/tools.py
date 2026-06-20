"""Cricket RAW tools — Phase 1.

All five tools follow the same pattern:
  validate args → call chain.fetch() → return tool_response(result)
No business logic here; that lives in models/.

Tools are bare async functions registered via ``register_cricket_tools(mcp)``
from ``server.py``; we avoid importing ``mcp`` at module load.
"""

from __future__ import annotations

from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.core.tool_response import Envelope, error_envelope, paginate, tool_response
from sportiq.cricket.chains import (
    fixtures_chain,
    live_score_chain,
    odds_chain,
    scorecard_chain,
    squad_chain,
    standings_chain,
)


def _filter_events_by_team(events: list[dict], team: str) -> list[dict]:
    """Case-insensitive substring match against both sides of each event."""
    q = team.strip().lower()
    return [
        e
        for e in events
        if q in (e.get("home") or "").lower() or q in (e.get("away") or "").lower()
    ]


async def cricket_get_live_matches() -> Envelope:
    """Return all currently live cricket matches across all series.

    Returns:
        data.matches: list of live match objects (team names, score, status).
        meta.source: which adapter served the response.
        meta.is_stale: true if data is from stale cache.
    """
    try:
        result = await live_score_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="No live-score source is available right now.",
            sources_tried=e.attempts,
            suggestion="Check sportiq_health() for adapter status.",
        )
    return tool_response(result)


async def cricket_get_scorecard(match_id: str) -> Envelope:
    """Return the full scorecard for a specific match.

    Args:
        match_id: The match identifier (e.g. from cricket_get_live_matches).

    Returns:
        data: full scorecard with innings, partnerships, bowling figures.
        meta.source: adapter that served the data.
    """
    if not match_id or not match_id.strip():
        return error_envelope(code="INVALID_INPUT", message="match_id must not be empty.")
    if len(match_id) > 100:
        return error_envelope(code="INVALID_INPUT", message="match_id must not exceed 100 characters.")
    try:
        result = await scorecard_chain.fetch(match_id=match_id.strip())
    except NotFoundError:
        return error_envelope(
            code="NOT_FOUND",
            message=f"No scorecard available for match {match_id!r}.",
        )
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch scorecard for match {match_id!r}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def cricket_get_points_table(series_id: str) -> Envelope:
    """Return the points table / standings for a cricket series.

    Args:
        series_id: The series identifier (e.g. IPL 2026 series ID from CricAPI).

    Returns:
        data: points table rows with team, P, W, L, NRR, Points.
        meta.source: adapter that served the data.
    """
    if not series_id or not series_id.strip():
        return error_envelope(code="INVALID_INPUT", message="series_id must not be empty.")
    if len(series_id) > 100:
        return error_envelope(code="INVALID_INPUT", message="series_id must not exceed 100 characters.")
    try:
        result = await standings_chain.fetch(series_id=series_id.strip())
    except NotFoundError:
        return error_envelope(
            code="NOT_FOUND",
            message=f"No points table available for series {series_id!r}.",
            suggestion="Bilateral series (e.g. a 3-match tour) have no points "
            "table — only league/round-robin series (IPL, World Cup group stage) "
            "do. Verify the series_id refers to a league via cricket_get_schedule.",
        )
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch points table for series {series_id!r}.",
            sources_tried=e.attempts,
            suggestion="If this is a bilateral series it has no points table; "
            "only league/round-robin series do. Otherwise the upstream may be "
            "down — check sportiq_health().",
        )
    return tool_response(result)


async def cricket_get_schedule(
    series_id: str | None = None, limit: int = 50, offset: int = 0
) -> Envelope:
    """Return the upcoming match schedule, optionally filtered by series.

    Args:
        series_id: Optional. Filter to a specific series. If omitted, returns
                   all upcoming fixtures across all active series.
        limit: Max matches to return, 1..200 (default 50).
        offset: Number of matches to skip for paging (default 0).

    Returns:
        data.matches: page of upcoming matches with teams, date, venue.
        data.pagination: {total, count, offset, limit, has_more, next_offset}.
        meta.source: adapter that served the data.
    """
    if not 1 <= limit <= 200:
        return error_envelope(code="INVALID_INPUT", message="limit must be in [1, 200].")
    if offset < 0:
        return error_envelope(code="INVALID_INPUT", message="offset must be >= 0.")
    try:
        result = await fixtures_chain.fetch(series_id=series_id)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="No schedule source is available right now.",
            sources_tried=e.attempts,
        )
    result.value = paginate(result.value, "matches", limit, offset)
    return tool_response(result)


async def cricket_get_squad(team: str, series_id: str | None = None) -> Envelope:
    """Return the squad roster for a cricket team, optionally for a specific series.

    Args:
        team: Team code or name (e.g. "MI", "CSK", "IND", "AUS").
        series_id: Optional. Series ID to pull the tournament-specific squad.
                   If omitted, falls back to static seed data.

    Returns:
        data.players: list of players with name, role, and credits.
        meta.source: adapter that served the data (cricapi / static_seed).
    """
    if not team or not team.strip():
        return error_envelope(code="INVALID_INPUT", message="team must not be empty.")
    if len(team) > 100:
        return error_envelope(code="INVALID_INPUT", message="team must not exceed 100 characters.")
    try:
        result = await squad_chain.fetch(team=team.strip(), series_id=series_id)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch squad for team {team!r}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def cricket_get_live_odds(team: str | None = None) -> Envelope:
    """Return live market head-to-head odds for upcoming/live IPL matches.

    Sourced from The Odds API (requires THEODDS_KEY). Without a key the call
    returns a clean ALL_SOURCES_FAILED envelope rather than crashing.

    Args:
        team: Optional team name to filter events (case-insensitive substring,
            matched against both sides). Omit to return every IPL event. The
            Odds API uses its own opaque event ids, so a CricAPI match_id
            cannot be resolved to an event yet — filtering is by team name.

    Returns:
        data.events: list of {event_id, home, away, commence_time, bookmakers:
            [{name, home, away}]} with decimal h2h prices per bookmaker.
        meta.source: adapter that served the data (theodds / cache:stale).
    """
    try:
        result = await odds_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="No cricket odds source is available right now.",
            sources_tried=e.attempts,
            suggestion="Set THEODDS_KEY to enable live odds.",
        )
    if team and team.strip():
        result.value = {"events": _filter_events_by_team(result.value["events"], team)}
    return tool_response(result)


def register_cricket_tools(mcp) -> None:
    """Register every cricket tool on the supplied FastMCP instance."""
    from sportiq.core.entitlements import gated
    from sportiq.core.tool_meta import READ_ONLY
    from sportiq.cricket.intel_tools import register_cricket_intel_tools

    mcp.tool(annotations=READ_ONLY)(cricket_get_live_matches)
    mcp.tool(annotations=READ_ONLY)(cricket_get_scorecard)
    mcp.tool(annotations=READ_ONLY)(cricket_get_points_table)
    mcp.tool(annotations=READ_ONLY)(cricket_get_schedule)
    mcp.tool(annotations=READ_ONLY)(cricket_get_squad)
    # Paid: burns the operator-funded THEODDS_KEY — gated to protect the quota.
    mcp.tool(annotations=READ_ONLY)(gated(cricket_get_live_odds))
    register_cricket_intel_tools(mcp)
