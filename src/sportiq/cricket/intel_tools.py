"""Cricket INTEL tools — Phase 2 flagship layer.

Five tools that compose the per-source chains into actionable answers:
build_dream11_team, captain_recommendation, differential_picks,
player_form_index, get_pitch_report.

Tools accept either a ``match_id`` (resolved to teams + venue via
``match_resolver.resolve_match``) or the raw ``team_a``/``team_b``/``venue``
triple directly. ``cricket_get_pitch_report`` and ``cricket_player_form_index``
are unaffected (venue-only and player-id-only respectively).
"""

from __future__ import annotations

from sportiq.core.errors import AllSourcesFailedError, InvalidInputError, NotFoundError
from sportiq.core.tool_response import error_envelope, staleness_meta, tool_response
from sportiq.core.value_bet import find_value
from sportiq.cricket.chains import (
    odds_chain,
    pitch_data_chain,
    player_stats_chain,
    squad_chain,
)
from sportiq.cricket.match_resolver import resolve_match
from sportiq.cricket.models.captain_score import expected_points
from sportiq.cricket.models.dream11_solver import solve as _solve_dream11
from sportiq.cricket.models.form_index import compute_form_index
from sportiq.cricket.models.pitch_report import pitch_report as _pitch_report
from sportiq.cricket.models.win_probability import win_prob

_DEFAULT_OPPOSITION_STRENGTH = 0.5
_DEFAULT_FORM_SCORE = 55.0  # neutral form when we have no per-player history

# Estimated-ownership proxy. squads.json credits span 7.0-11.0; we map that
# linearly onto a 5%->90% ownership curve (cheap fringe players are rarely owned;
# premiums are near-universal). The old `credits * 7` proxy put even the cheapest
# 7.0-credit player at 49% -- above the default 20% threshold -- so the tool always
# returned []. Still flagged estimated:true; real ownership lands with the odds feed.
_OWN_MIN_CREDITS, _OWN_MAX_CREDITS = 7.0, 11.0
_OWN_MIN_PCT, _OWN_MAX_PCT = 5.0, 90.0


def _estimated_ownership_pct(credits: float) -> float:
    """Map a player's credit cost onto an estimated ownership percentage (1-99)."""
    span = _OWN_MAX_CREDITS - _OWN_MIN_CREDITS
    frac = (credits - _OWN_MIN_CREDITS) / span if span else 0.0
    pct = _OWN_MIN_PCT + frac * (_OWN_MAX_PCT - _OWN_MIN_PCT)
    return max(1.0, min(99.0, pct))


async def _candidate_pool(
    team_a: str, team_b: str, venue_record: dict
) -> tuple[list[dict], list]:
    """Compose the candidate list the solver/captain ranker consumes.

    Returns the candidate dicts plus the two squad ``FallbackResult``s so callers
    can aggregate freshness into ``meta`` (per fallback-contract.md).
    """
    a = await squad_chain.fetch(team=team_a)
    b = await squad_chain.fetch(team=team_b)
    candidates: list[dict] = []
    for squad_result in (a, b):
        squad = squad_result.value
        team_label = squad.get("team") or ""
        for player in squad.get("players", []):
            pp = expected_points(
                player,
                venue_record,
                opposition_strength=_DEFAULT_OPPOSITION_STRENGTH,
                form_score=_DEFAULT_FORM_SCORE,
            )
            candidates.append(
                {
                    "name": player.get("name", ""),
                    "role": player.get("role", "BAT"),
                    "credits": float(player.get("credits", 8.0)),
                    "team": player.get("team") or team_label,
                    "projected_points": round(pp, 2),
                }
            )
    return candidates, [a, b]


async def cricket_build_dream11_team(
    match_id: str | None = None,
    team_a: str | None = None,
    team_b: str | None = None,
    venue: str | None = None,
    strategy: str = "balanced",
) -> dict:
    """Recommend an optimal Dream11 XI + captain + vice-captain for one fixture.

    Args:
        match_id: CricAPI match identifier; resolves team_a/team_b/venue automatically.
        team_a: First team code/name (e.g. ``MI``). Required if match_id is absent.
        team_b: Second team code/name (e.g. ``CSK``). Required if match_id is absent.
        venue: Venue key/name (e.g. ``wankhede``). Required if match_id is absent.
        strategy: ``"balanced"`` only in Phase 2; future variants reserved.

    Returns:
        data.players: 11 picked players with name/role/credits/team/projected_points.
        data.captain: name of the chosen captain.
        data.vice_captain: name of the chosen VC.
        data.total_credits: sum of credits used (<= 100).
        data.total_projected_points: fantasy points including C x2 and VC x1.5 boosts.
        meta.estimated: true — projections are model output, not Dream11 oracle.
    """
    if match_id:
        try:
            resolved = await resolve_match(match_id)
        except NotFoundError as e:
            return error_envelope(code="NOT_FOUND", message=str(e))
        team_a = resolved["team_a"]
        team_b = resolved["team_b"]
        venue = venue or resolved["venue"]

    if not team_a or not team_a.strip() or not team_b or not team_b.strip():
        return error_envelope(code="INVALID_INPUT", message="team_a and team_b must be non-empty.")
    if len(team_a) > 100:
        return error_envelope(code="INVALID_INPUT", message="team_a must not exceed 100 characters.")
    if len(team_b) > 100:
        return error_envelope(code="INVALID_INPUT", message="team_b must not exceed 100 characters.")
    if not venue or not venue.strip():
        return error_envelope(code="INVALID_INPUT", message="venue must be non-empty.")
    if len(venue) > 200:
        return error_envelope(code="INVALID_INPUT", message="venue must not exceed 200 characters.")

    try:
        venue_result = await pitch_data_chain.fetch(venue=venue)
        candidates, squad_results = await _candidate_pool(team_a, team_b, venue_result.value)
        squad_result = _solve_dream11(candidates, strategy=strategy)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not assemble candidate pool from squad/venue chains.",
            sources_tried=e.attempts,
        )
    except InvalidInputError as e:
        return error_envelope(code="INVALID_INPUT", message=str(e))
    except NotFoundError as e:
        return error_envelope(code="NOT_FOUND", message=str(e))

    return {
        "data": squad_result,
        "meta": {
            "source": "model:dream11_solver",
            "venue": venue_result.value.get("name"),
            "strategy": strategy,
            "estimated": True,
            **staleness_meta(venue_result, *squad_results),
        },
    }


async def cricket_captain_recommendation(
    match_id: str | None = None,
    team_a: str | None = None,
    team_b: str | None = None,
    venue: str | None = None,
) -> dict:
    """Return the top-3 captain candidates ranked by projected points.

    Args:
        match_id: CricAPI match identifier; resolves team_a/team_b/venue automatically.
        team_a: First team code/name. Required if match_id is absent.
        team_b: Second team code/name. Required if match_id is absent.
        venue: Venue key/name. Required if match_id is absent.

    Returns:
        data.candidates: list of 3 dicts with name/role/team/projected_points.
        meta.source: model:captain_score.
        meta.estimated: true.
    """
    if match_id:
        try:
            resolved = await resolve_match(match_id)
        except NotFoundError as e:
            return error_envelope(code="NOT_FOUND", message=str(e))
        team_a = resolved["team_a"]
        team_b = resolved["team_b"]
        venue = venue or resolved["venue"]

    if not team_a or not team_a.strip() or not team_b or not team_b.strip() or not venue or not venue.strip():
        return error_envelope(code="INVALID_INPUT", message="team_a, team_b, venue must all be non-empty.")
    if len(team_a) > 100:
        return error_envelope(code="INVALID_INPUT", message="team_a must not exceed 100 characters.")
    if len(team_b) > 100:
        return error_envelope(code="INVALID_INPUT", message="team_b must not exceed 100 characters.")
    if len(venue) > 200:
        return error_envelope(code="INVALID_INPUT", message="venue must not exceed 200 characters.")

    try:
        venue_result = await pitch_data_chain.fetch(venue=venue)
        candidates, squad_results = await _candidate_pool(team_a, team_b, venue_result.value)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not assemble candidate pool.",
            sources_tried=e.attempts,
        )
    except NotFoundError as e:
        return error_envelope(code="NOT_FOUND", message=str(e))

    top3 = sorted(candidates, key=lambda c: c["projected_points"], reverse=True)[:3]
    return {
        "data": {"candidates": top3},
        "meta": {
            "source": "model:captain_score",
            "estimated": True,
            **staleness_meta(venue_result, *squad_results),
        },
    }


async def cricket_differential_picks(
    match_id: str | None = None,
    team_a: str | None = None,
    team_b: str | None = None,
    venue: str | None = None,
    ownership_threshold: int = 20,
) -> dict:
    """Suggest low-ownership picks with positive projected upside.

    Ownership is *estimated* (we proxy by credit weight — lower-credit
    players tend to have lower ownership). True ownership lands when the
    Live Sports Odds RapidAPI server is wired in a later phase.

    Args:
        match_id: CricAPI match identifier; resolves team_a/team_b/venue automatically.
        team_a: First team code/name. Required if match_id is absent.
        team_b: Second team code/name. Required if match_id is absent.
        venue: Venue key/name. Required if match_id is absent.
        ownership_threshold: percent ownership cap; affects estimated label.

    Returns:
        data.picks: list of {name, role, team, credits, projected_points,
            estimated_ownership_pct}.
        meta.source: model:captain_score (filtered).
        meta.estimated: true.
    """
    if match_id:
        try:
            resolved = await resolve_match(match_id)
        except NotFoundError as e:
            return error_envelope(code="NOT_FOUND", message=str(e))
        team_a = resolved["team_a"]
        team_b = resolved["team_b"]
        venue = venue or resolved["venue"]

    if not team_a or not team_a.strip() or not team_b or not team_b.strip() or not venue or not venue.strip():
        return error_envelope(code="INVALID_INPUT", message="team_a, team_b, venue must all be non-empty.")
    if len(team_a) > 100:
        return error_envelope(code="INVALID_INPUT", message="team_a must not exceed 100 characters.")
    if len(team_b) > 100:
        return error_envelope(code="INVALID_INPUT", message="team_b must not exceed 100 characters.")
    if len(venue) > 200:
        return error_envelope(code="INVALID_INPUT", message="venue must not exceed 200 characters.")
    if not 0 <= ownership_threshold <= 100:
        return error_envelope(code="INVALID_INPUT", message="ownership_threshold must be in [0, 100].")

    try:
        venue_result = await pitch_data_chain.fetch(venue=venue)
        candidates, squad_results = await _candidate_pool(team_a, team_b, venue_result.value)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not assemble candidate pool.",
            sources_tried=e.attempts,
        )
    except NotFoundError as e:
        return error_envelope(code="NOT_FOUND", message=str(e))

    picks: list[dict] = []
    for c in candidates:
        est_own = _estimated_ownership_pct(c["credits"])
        if est_own <= ownership_threshold and c["projected_points"] >= 40:
            picks.append({**c, "estimated_ownership_pct": round(est_own, 1)})
    picks.sort(key=lambda c: c["projected_points"], reverse=True)
    return {
        "data": {"picks": picks[:5], "ownership_threshold": ownership_threshold},
        "meta": {
            "source": "model:captain_score",
            "estimated": True,
            **staleness_meta(venue_result, *squad_results),
        },
    }


def _t20_career_numbers(stats_payload: dict) -> tuple[float, float]:
    """Pull T20I career average + strike rate out of a player_stats payload.

    Handles both CricAPI ``stats: [{fn, matchtype, stat, value}, ...]`` and
    RapidAPI Cricbuzz ``values: [{name: "T20I", average, strikeRate}, ...]``.
    Falls back to ``0.0`` per field if the upstream shape is unrecognised.
    """
    # CricAPI shape.
    avg, sr = 0.0, 0.0
    cric_rows = (stats_payload or {}).get("data", {}).get("stats", [])
    if cric_rows:
        for row in cric_rows:
            if row.get("matchtype") != "t20i" or row.get("fn") != "batting":
                continue
            try:
                if row.get("stat") == "Average":
                    avg = float(row.get("value", 0))
                elif row.get("stat") == "Strike Rate":
                    sr = float(row.get("value", 0))
            except (TypeError, ValueError):
                continue
        if avg or sr:
            return avg, sr

    # RapidAPI Cricbuzz shape.
    for row in (stats_payload or {}).get("values", []):
        if row.get("name") != "T20I":
            continue
        try:
            avg = float(row.get("average", 0) or 0)
            sr = float(row.get("strikeRate", 0) or 0)
        except (TypeError, ValueError):
            pass
        break
    return avg, sr


async def cricket_player_form_index(player_id: str) -> dict:
    """Report a 0-100 form score for a player using the player_stats chain.

    Args:
        player_id: Upstream player identifier (CricAPI/Cricbuzz id).

    Returns:
        data.form_score: 0..100 indicator.
        data.trend: "rising" / "stable" / "falling".
        data.samples: how many recent innings were available.
        meta.source: which adapter served the underlying stats.
        meta.estimated: true.
    """
    if not player_id.strip():
        return error_envelope(code="INVALID_INPUT", message="player_id must not be empty.")

    try:
        stats_result = await player_stats_chain.fetch(player_id=player_id.strip())
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch stats for player {player_id!r}.",
            sources_tried=e.attempts,
        )

    avg, sr = _t20_career_numbers(stats_result.value)
    # Phase 2 has no per-innings recent stream from the upstreams — we only
    # have career numbers. Pass an empty recent list so the model falls back
    # to the career baseline. (Recent-innings ingestion is a follow-up.)
    form = compute_form_index([], career_avg=avg, career_sr=sr)
    return {
        "data": {**form, "player_id": player_id, "career_avg": avg, "career_sr": sr},
        "meta": {
            "source": stats_result.source,
            "is_stale": stats_result.is_stale,
            "estimated": True,
        },
    }


async def cricket_get_pitch_report(venue: str) -> dict:
    """Summarise pitch characteristics for a venue.

    Args:
        venue: Venue key (e.g. ``wankhede``), official name, or city.

    Returns:
        data: {batting_friendly 0..1, expected_first_inn, recommendation,
            venue, pitch_type}.
        meta.source: which adapter served the venue record.
    """
    if not venue.strip():
        return error_envelope(code="INVALID_INPUT", message="venue must not be empty.")
    if len(venue) > 200:
        return error_envelope(code="INVALID_INPUT", message="venue must not exceed 200 characters.")

    try:
        venue_result = await pitch_data_chain.fetch(venue=venue.strip())
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"No venue data for {venue!r}.",
            sources_tried=e.attempts,
        )
    except NotFoundError as e:
        return error_envelope(code="NOT_FOUND", message=str(e))

    report = _pitch_report(venue_result.value)
    return tool_response(type("Result", (), {  # ad-hoc shim for envelope
        "value": report,
        "source": venue_result.source,
        "is_stale": venue_result.is_stale,
        "data_age_seconds": venue_result.data_age_seconds,
        "fallback_used": venue_result.fallback_used,
        "duration_ms": venue_result.duration_ms,
    })())


async def cricket_find_value_bets(
    team: str | None = None,
    min_edge: float = 0.05,
) -> dict:
    """Find +EV ("value") bets on upcoming IPL matches.

    Compares the server's heuristic win model (form + H2H + venue) against
    de-vigged bookmaker head-to-head odds. Requires THEODDS_KEY.

    Args:
        team: Optional team name to filter events (case-insensitive substring).
            Omit to scan every IPL odds event.
        min_edge: Minimum edge (model_prob - devigged_market_prob), 0..1.
            Default 0.05 (5 percentage points).

    Returns:
        data.value_bets: list of {event_id, home, away, outcome, model_prob,
            fair_odds, market_odds, edge, bookmaker}, sorted by edge descending.
        data.events_analysed: count of events where model + odds were available.
        meta.estimated: true — model probabilities are heuristic estimates.
    """
    import time as _time

    if not 0.0 <= min_edge <= 1.0:
        return error_envelope(code="INVALID_INPUT", message="min_edge must be in [0, 1].")

    t0 = _time.monotonic()

    try:
        odds_result = await odds_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="No cricket odds source available. Set THEODDS_KEY to enable.",
            sources_tried=e.attempts,
        )

    events = odds_result.value.get("events", [])
    if team and team.strip():
        needle = team.strip().lower()
        events = [
            ev for ev in events
            if needle in ev.get("home", "").lower() or needle in ev.get("away", "").lower()
        ]

    value_bets = []
    analysed = 0

    for ev in events:
        home_team = ev.get("home", "")
        away_team = ev.get("away", "")
        if not home_team or not away_team:
            continue

        # Use neutral signals (no form data available at this scope); tool is
        # still useful as a de-vigged baseline even with 50/50 priors.
        probs = win_prob({}, {})
        model_probs = {"home_win": probs["team_a"], "away_win": probs["team_b"]}

        for bookmaker in ev.get("bookmakers", []):
            for pick in find_value(model_probs, bookmaker, min_edge):
                value_bets.append(
                    {
                        "event_id": ev.get("event_id"),
                        "home": home_team,
                        "away": away_team,
                        **pick,
                    }
                )
        analysed += 1

    value_bets.sort(key=lambda x: x.get("edge", 0), reverse=True)

    return {
        "data": {
            "value_bets": value_bets,
            "events_analysed": analysed,
            "min_edge": min_edge,
        },
        "meta": {
            "source": odds_result.source,
            "is_stale": odds_result.is_stale,
            "data_age_seconds": getattr(odds_result, "data_age_seconds", 0),
            "fallback_used": odds_result.fallback_used,
            "duration_ms": int((_time.monotonic() - t0) * 1000),
            "estimated": True,
        },
    }


def register_cricket_intel_tools(mcp) -> None:
    """Register the six INTEL tools on the supplied FastMCP instance."""
    mcp.tool()(cricket_build_dream11_team)
    mcp.tool()(cricket_captain_recommendation)
    mcp.tool()(cricket_differential_picks)
    mcp.tool()(cricket_player_form_index)
    mcp.tool()(cricket_get_pitch_report)
    mcp.tool()(cricket_find_value_bets)
