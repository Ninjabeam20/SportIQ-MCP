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

import asyncio

from sportiq.core.errors import AllSourcesFailedError, InvalidInputError, NotFoundError
from sportiq.core.tool_response import Envelope, error_envelope, staleness_meta, tool_response
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
from sportiq.cricket.models.head_to_head import summarise_h2h
from sportiq.cricket.models.pitch_report import pitch_report as _pitch_report
from sportiq.cricket.models.player_matchup import compute_matchup as _compute_matchup
from sportiq.cricket.models.win_probability import win_prob

# Cap concurrent per-player stats fetches during H2H analysis.
_PLAYER_STATS_SEMAPHORE = asyncio.Semaphore(5)

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
    # Independent fetches — gather so a cold cache costs one round-trip, not two.
    a, b = await asyncio.gather(
        squad_chain.fetch(team=team_a), squad_chain.fetch(team=team_b)
    )
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
) -> Envelope:
    """Recommend an optimal fantasy XI + captain + vice-captain for one fixture.

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
        meta.estimated: true — projections are model output, not a fantasy oracle.

    Example:
        cricket_build_dream11_team(team_a="MI", team_b="CSK", venue="wankhede")
        cricket_build_dream11_team(match_id="abc123")
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
) -> Envelope:
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
) -> Envelope:
    """Suggest low-ownership picks with positive projected upside.

    Ownership is *estimated* — proxied by credit weight (lower-credit players
    tend to have lower ownership), not real ownership data. Flagged
    ``estimated: true`` in the response.

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


async def cricket_player_form_index(player_id: str) -> Envelope:
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


async def cricket_get_pitch_report(venue: str) -> Envelope:
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

    # Build the envelope from venue_result (carries source/staleness), then swap
    # the raw venue record for the computed pitch report — no result shim needed.
    resp = tool_response(venue_result)
    resp["data"] = _pitch_report(venue_result.value)
    return resp


async def _fetch_player_stats_safe(pid: str) -> tuple[str, dict]:
    """Fetch stats for one player, gated by the concurrency semaphore.

    Returns ``(pid, stats_dict)`` on success or ``(pid, {})`` on any failure
    so callers can always unpack a 2-tuple.
    """
    async with _PLAYER_STATS_SEMAPHORE:
        try:
            result = await player_stats_chain.fetch(player_id=pid)
            return pid, result.value
        except Exception:  # best-effort; skip broken sources
            return pid, {}


async def cricket_head_to_head(team_a: str, team_b: str) -> Envelope:
    """Compare two cricket teams head-to-head using squad form and player stats.

    Args:
        team_a: First team code or name (e.g. "MI", "India").
        team_b: Second team code or name (e.g. "CSK", "Australia").

    Returns:
        data: {team_a, team_b, team_a_edge_count, team_b_edge_count,
               key_players_a, key_players_b, h2h_win_rate_a, h2h_win_rate_b,
               win_prob_a, win_prob_b}.
        meta.estimated: true.
    """
    if not team_a or not team_a.strip():
        return error_envelope(code="INVALID_INPUT", message="team_a must not be empty.")
    if not team_b or not team_b.strip():
        return error_envelope(code="INVALID_INPUT", message="team_b must not be empty.")
    if team_a.strip().lower() == team_b.strip().lower():
        return error_envelope(code="INVALID_INPUT", message="team_a and team_b must be different.")

    # --- fetch squads (independent — gather) ---
    try:
        squad_result_a, squad_result_b = await asyncio.gather(
            squad_chain.fetch(team=team_a.strip()),
            squad_chain.fetch(team=team_b.strip()),
        )
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch squad data.",
            sources_tried=e.attempts,
        )

    squad_a_players: list[dict] = squad_result_a.value.get("players", [])
    squad_b_players: list[dict] = squad_result_b.value.get("players", [])

    # --- fetch player stats concurrently (best-effort, up to 11 per side) ---
    def _pids(players: list[dict]) -> list[str]:
        pids = []
        for p in players[:11]:
            pid = p.get("player_id") or p.get("id")
            if pid:
                pids.append(str(pid))
        return pids

    all_pids = _pids(squad_a_players) + _pids(squad_b_players)
    if all_pids:
        fetch_results = await asyncio.gather(
            *[_fetch_player_stats_safe(pid) for pid in all_pids],
            return_exceptions=True,
        )
        stats_by_player: dict[str, dict] = {}
        for item in fetch_results:
            if isinstance(item, Exception):
                continue
            pid, stats = item
            if stats:
                stats_by_player[pid] = stats
    else:
        stats_by_player = {}

    # --- derive H2H summary ---
    h2h_result = summarise_h2h(
        team_a.strip(),
        team_b.strip(),
        squad_a_players,
        squad_b_players,
        stats_by_player,
    )

    # --- win probability from H2H edge ratio ---
    probs = win_prob(
        {"h2h_win_rate": h2h_result["h2h_win_rate_a"]},
        {"h2h_win_rate": h2h_result["h2h_win_rate_b"]},
    )

    return {
        "data": {
            **h2h_result,
            "win_prob_a": probs["team_a"],
            "win_prob_b": probs["team_b"],
        },
        "meta": {
            "source": squad_result_a.source,
            "is_stale": squad_result_a.is_stale or squad_result_b.is_stale,
            "estimated": True,
            **staleness_meta(squad_result_a, squad_result_b),
        },
    }


async def cricket_find_value_bets(
    team: str | None = None,
    min_edge: float = 0.05,
) -> Envelope:
    """Compare model probabilities against market-implied IPL odds. Requires THEODDS_KEY.

    NOTE: cricket has no calibrated team-strength model wired yet (unlike the
    football Elo/Poisson path), so this tool currently returns an EMPTY
    ``value_bets`` list — scoring an edge against a neutral 50/50 prior would flag
    every market underdog, which would be misleading. It
    still reports how many events were screened so callers know odds were
    available. For raw de-vigged prices use ``cricket_get_live_odds``. Real edge
    detection lands when a cricket win model is wired (see cricket_head_to_head).

    Args:
        team: Optional team name to filter events (case-insensitive substring).
            Omit to scan every IPL odds event.
        min_edge: Minimum edge (model_prob - devigged_market_prob), 0..1.
            Default 0.05. Currently informational only (no bets emitted).

    Returns:
        data.value_bets: always ``[]`` until a cricket model is wired.
        data.events_analysed: count of events screened (both teams present).
        data.model: ``"neutral_baseline"``. data.note: why no bets are emitted.
        meta.estimated: true.
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

    # Cricket has no calibrated team-strength model wired yet (unlike football's
    # Elo/Poisson path). Scoring "value" against a neutral 50/50 prior would flag
    # every market underdog as +EV — false confidence in a betting tool. So we
    # screen the events for de-vig readiness but emit NO value bets until a real
    # model lands (the eventual signal source is cricket_head_to_head's win_prob).
    analysed = sum(1 for ev in events if ev.get("home") and ev.get("away"))

    return {
        "data": {
            "value_bets": [],
            "events_analysed": analysed,
            "min_edge": min_edge,
            "model": "neutral_baseline",
            "note": (
                "No calibrated cricket win model yet; value detection is disabled "
                "to avoid false positives from a neutral 50/50 prior. Use "
                "cricket_get_live_odds for de-vigged market prices."
            ),
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


async def cricket_player_matchup(player_a: str, player_b: str) -> Envelope:
    """Analyse the head-to-head matchup between two cricket players based on role and career stats.

    Args:
        player_a: Player ID or name for the first player.
        player_b: Player ID or name for the second player.

    Returns:
        data: {matchup_type, edge_holder, edge_reason, signals, role_a, role_b}.
        meta.estimated: true — heuristic model, not ball-by-ball H2H data.
    """
    if not player_a or not player_a.strip():
        return error_envelope(code="INVALID_INPUT", message="player_a must not be empty.")
    if not player_b or not player_b.strip():
        return error_envelope(code="INVALID_INPUT", message="player_b must not be empty.")
    if player_a.strip() == player_b.strip():
        return error_envelope(code="INVALID_INPUT", message="player_a and player_b must be different.")

    stats_a_r, stats_b_r = await asyncio.gather(
        player_stats_chain.fetch(player_id=player_a.strip()),
        player_stats_chain.fetch(player_id=player_b.strip()),
        return_exceptions=True,
    )

    if isinstance(stats_a_r, NotFoundError) or isinstance(stats_b_r, NotFoundError):
        nf = stats_a_r if isinstance(stats_a_r, NotFoundError) else stats_b_r
        return error_envelope(code="NOT_FOUND", message=str(nf))
    if isinstance(stats_a_r, Exception) or isinstance(stats_b_r, Exception):
        return error_envelope(code="ALL_SOURCES_FAILED", message="Could not fetch player stats.")

    result = _compute_matchup(stats_a_r.value, stats_b_r.value)
    return {
        "data": result,
        "meta": {
            "source": stats_a_r.source,
            "estimated": True,
            **staleness_meta(stats_a_r, stats_b_r),
        },
    }


def register_cricket_intel_tools(mcp) -> None:
    """Register the eight INTEL tools on the supplied FastMCP instance.

    Every cricket intel tool is paid — wrapped in ``gated`` so it requires an
    active ``SPORTIQ_PRO_KEY`` (V1 honor-system gate).
    """
    from sportiq.core.entitlements import gated
    from sportiq.core.tool_meta import READ_ONLY

    mcp.tool(annotations=READ_ONLY)(gated(cricket_build_dream11_team))
    mcp.tool(annotations=READ_ONLY)(gated(cricket_captain_recommendation))
    mcp.tool(annotations=READ_ONLY)(gated(cricket_differential_picks))
    mcp.tool(annotations=READ_ONLY)(gated(cricket_player_form_index))
    mcp.tool(annotations=READ_ONLY)(gated(cricket_get_pitch_report))
    mcp.tool(annotations=READ_ONLY)(gated(cricket_find_value_bets))
    mcp.tool(annotations=READ_ONLY)(gated(cricket_head_to_head))
    mcp.tool(annotations=READ_ONLY)(gated(cricket_player_matchup))
