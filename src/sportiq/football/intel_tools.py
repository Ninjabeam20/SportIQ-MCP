"""Football INTEL tools — Phase 4 flagship layer.

Five tools composing the static draw + Elo ratings with the Poisson/Monte-Carlo
models. Flagship: football_simulate_bracket. All route through
football_groups_chain (the source of the draw + ratings) and surface is_stale.
"""
from __future__ import annotations

import asyncio

from sportiq.config import settings
from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.core.parlay import build_accumulator
from sportiq.core.tool_response import Envelope, error_envelope, staleness_meta
from sportiq.football.chains import (
    football_fixtures_chain,
    football_groups_chain,
    football_odds_chain,
)
from sportiq.football.models import poisson_xg
from sportiq.football.models.bracket_sim import simulate_tournament
from sportiq.football.models.elo_live import nudge_ratings
from sportiq.football.models.form_trends import compute_form_trends
from sportiq.football.models.group_sim import simulate_group as _simulate_group
from sportiq.football.models.results_state import ResultsState, build_results_state
from sportiq.football.models.value_bet import find_value

_MAX_ITERATIONS = 20000
_MIN_ITERATIONS = 100

_NO_LIVE_NOTE = "Live results unavailable; simulated from the pre-tournament seed."


async def _groups_payload() -> dict:
    """Fetch the draw + ratings, or raise AllSourcesFailedError."""
    return await football_groups_chain.fetch()


def _clamp_iterations(iterations: int) -> int:
    return max(_MIN_ITERATIONS, min(_MAX_ITERATIONS, iterations))


async def _fetch_live_state(groups_value: dict) -> tuple[ResultsState | None, object | None]:
    """Fetch live fixtures and map them onto this draw.

    Returns ``(state, fixtures_result)``, or ``(None, None)`` if no fixture
    source is available (callers then fall back to the from-scratch sim).
    """
    try:
        fixtures_result = await football_fixtures_chain.fetch()
    except (AllSourcesFailedError, NotFoundError):
        return None, None
    try:
        state = build_results_state(
            fixtures_result.value.get("fixtures", []),
            groups_value.get("groups", {}),
            groups_value.get("teams", {}),
        )
    except Exception:
        # A drifted upstream shape (e.g. non-numeric goals) must not crash the
        # tool — degrade to the from-scratch sim, same as no fixture source.
        return None, None
    return state, fixtures_result


def _conditioned_ratings(base_ratings: dict, state: ResultsState | None) -> dict:
    """Apply the opt-in in-tournament Elo nudge when enabled and results exist."""
    if settings.football_live_elo and state is not None:
        return nudge_ratings(base_ratings, state.completed_chrono)
    return base_ratings


async def _maybe_nudge_single(groups_value: dict, ratings: dict) -> tuple[dict, bool]:
    """For single-match tools: nudge ratings from live results when enabled.

    Returns ``(ratings, live_elo_applied)``. No conditioning structure is needed
    here — these tools score one matchup, so only the rating shift matters.
    """
    if not settings.football_live_elo:
        return ratings, False
    state, _ = await _fetch_live_state(groups_value)
    if state is None:
        return ratings, False
    return nudge_ratings(ratings, state.completed_chrono), True


def _sim_meta(groups_result, fixtures_result, state: ResultsState | None) -> dict:
    """Build the meta envelope for a conditioned simulation tool."""
    sources = [groups_result] + ([fixtures_result] if fixtures_result is not None else [])
    meta: dict = {
        "source": groups_result.source,
        "estimated": True,
        "conditioned_matches": state.matched if state else 0,
        **staleness_meta(*sources),
    }
    if state and state.dropped:
        meta["fixtures_dropped"] = state.dropped
    if settings.football_live_elo and state is not None:
        meta["live_elo"] = True
    if state is None:
        meta["note"] = _NO_LIVE_NOTE
    return meta


async def football_xg_model(home_team: str, away_team: str, neutral: bool = True) -> Envelope:
    """Estimate a match's expected goals and win/draw/loss probabilities.

    Args:
        home_team: First team code (e.g. "ARG").
        away_team: Second team code (e.g. "BRA").
        neutral: True for a neutral venue (no home advantage). World Cup default.

    Returns:
        data: {expected_home_goals, expected_away_goals, home_win, draw, away_win}.
        meta.estimated: true.
    """
    if len(home_team) > 100:
        return error_envelope(code="INVALID_INPUT", message="home_team must not exceed 100 characters.")
    if len(away_team) > 100:
        return error_envelope(code="INVALID_INPUT", message="away_team must not exceed 100 characters.")
    home, away = home_team.upper(), away_team.upper()

    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(code=e.code, message="Could not load ratings.", sources_tried=e.attempts)

    ratings = result.value.get("ratings", {})
    if home not in ratings or away not in ratings:
        return error_envelope(code="NOT_FOUND", message="Unknown team code; see football_get_groups.")
    ratings, live_elo = await _maybe_nudge_single(result.value, ratings)

    home_adv = 0.0 if neutral else 60.0
    lam_h, lam_a = poisson_xg.lambdas_from_elo(ratings[home], ratings[away], home_adv)
    outcome = poisson_xg.outcome_probabilities(lam_h, lam_a)
    meta = {"source": result.source, "estimated": True, **staleness_meta(result)}
    if live_elo:
        meta["live_elo"] = True
    return {
        "data": {
            "home_team": home,
            "away_team": away,
            "expected_home_goals": round(lam_h, 3),
            "expected_away_goals": round(lam_a, 3),
            **outcome,
        },
        "meta": meta,
    }


async def football_match_predictor(home_team: str, away_team: str, neutral: bool = True) -> Envelope:
    """Predict a single match: most likely scoreline + outcome probabilities.

    Args:
        home_team: First team code.
        away_team: Second team code.
        neutral: True for a neutral venue (World Cup default).

    Returns:
        data: {most_likely_score, home_win, draw, away_win, predicted_winner}.
        meta.estimated: true.
    """
    if len(home_team) > 100:
        return error_envelope(code="INVALID_INPUT", message="home_team must not exceed 100 characters.")
    if len(away_team) > 100:
        return error_envelope(code="INVALID_INPUT", message="away_team must not exceed 100 characters.")
    home, away = home_team.upper(), away_team.upper()

    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(code=e.code, message="Could not load ratings.", sources_tried=e.attempts)

    ratings = result.value.get("ratings", {})
    if home not in ratings or away not in ratings:
        return error_envelope(code="NOT_FOUND", message="Unknown team code; see football_get_groups.")
    ratings, live_elo = await _maybe_nudge_single(result.value, ratings)

    home_adv = 0.0 if neutral else 60.0
    lam_h, lam_a = poisson_xg.lambdas_from_elo(ratings[home], ratings[away], home_adv)
    outcome = poisson_xg.outcome_probabilities(lam_h, lam_a)
    gh, ga = poisson_xg.most_likely_scoreline(lam_h, lam_a)
    if outcome["home_win"] >= outcome["away_win"] and outcome["home_win"] >= outcome["draw"]:
        winner = home
    elif outcome["away_win"] >= outcome["draw"]:
        winner = away
    else:
        winner = "DRAW"
    meta = {"source": result.source, "estimated": True, **staleness_meta(result)}
    if live_elo:
        meta["live_elo"] = True
    return {
        "data": {
            "home_team": home,
            "away_team": away,
            "most_likely_score": f"{gh}-{ga}",
            "predicted_winner": winner,
            **outcome,
        },
        "meta": meta,
    }


async def football_simulate_group(group: str, iterations: int = 5000) -> Envelope:
    """Monte Carlo one group's round-robin -> per-team qualification probabilities.

    Args:
        group: Group letter A-L.
        iterations: Number of simulations (clamped to 100..20000).

    Returns:
        data.teams: {code: {p_first, p_second, p_third, p_fourth, p_advance, avg_points}}.
        data.iterations: iterations actually run.
        meta.estimated: true. meta.conditioned_matches: completed matches locked in.
    """
    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(code=e.code, message="Could not load draw.", sources_tried=e.attempts)

    groups = result.value.get("groups", {})
    key = group.upper()
    if key not in groups:
        return error_envelope(code="NOT_FOUND", message=f"Unknown group {group!r}; groups are A-L.")

    state, fixtures_result = await _fetch_live_state(result.value)
    ratings = _conditioned_ratings(result.value.get("ratings", {}), state)
    known = state.groups.get(key) if state else None

    sim = _simulate_group(groups[key], ratings, n_iter=_clamp_iterations(iterations), known=known)
    meta = _sim_meta(result, fixtures_result, state)
    if state:  # group-tool count should reflect only this group's locked matches
        meta["conditioned_matches"] = len(known.completed) if known else 0
    return {"data": {"group": key, **sim}, "meta": meta}


async def football_simulate_bracket(iterations: int = 10000, seed: int | None = None) -> Envelope:
    """Monte Carlo the full World Cup 2026 — per-team round + title probabilities.

    Simulates all 12 groups, advances the top 2 + 8 best third-placed teams to a
    32-team knockout, and plays it to a champion, ``iterations`` times.

    Args:
        iterations: Number of tournament simulations (clamped to 100..20000;
            ~10000 gives stable ±2% probabilities).
        seed: Optional RNG seed for reproducible output.

    Returns:
        data.teams: {code: {reach_r32, reach_r16, reach_qf, reach_sf, reach_final, win}}
            sorted by win probability descending.
        data.champion: most likely winner.
        data.iterations: iterations run.
        meta.estimated: true. meta.conditioned_matches: completed matches locked in
            (played group results fixed, decided knockout ties locked).

    Example:
        football_simulate_bracket()
        football_simulate_bracket(iterations=20000, seed=42)
    """
    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(code=e.code, message="Could not load draw.", sources_tried=e.attempts)

    groups = result.value.get("groups", {})
    state, fixtures_result = await _fetch_live_state(result.value)
    ratings = _conditioned_ratings(result.value.get("ratings", {}), state)
    sim = simulate_tournament(
        groups, ratings, n_iter=_clamp_iterations(iterations), seed=seed, results=state
    )
    return {"data": sim, "meta": _sim_meta(result, fixtures_result, state)}


async def football_knockout_path(team: str, iterations: int = 10000, seed: int | None = None) -> Envelope:
    """Round-by-round survival probabilities for one team in the full sim.

    Args:
        team: Team code (e.g. "FRA").
        iterations: Number of tournament simulations (clamped to 100..20000).
        seed: Optional RNG seed.

    Returns:
        data: {team, reach_r32, reach_r16, reach_qf, reach_sf, reach_final, win}.
        meta.estimated: true.
    """
    if len(team) > 100:
        return error_envelope(code="INVALID_INPUT", message="team must not exceed 100 characters.")
    code = team.upper()

    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(code=e.code, message="Could not load draw.", sources_tried=e.attempts)

    groups = result.value.get("groups", {})
    base_ratings = result.value.get("ratings", {})
    if code not in base_ratings:
        return error_envelope(code="NOT_FOUND", message="Unknown team code; see football_get_groups.")

    state, fixtures_result = await _fetch_live_state(result.value)
    ratings = _conditioned_ratings(base_ratings, state)
    sim = simulate_tournament(
        groups, ratings, n_iter=_clamp_iterations(iterations), seed=seed, results=state
    )
    row = sim["teams"].get(code, {})
    return {"data": {"team": code, **row}, "meta": _sim_meta(result, fixtures_result, state)}


async def football_find_value_bets(team: str | None = None, min_edge: float = 0.05) -> Envelope:
    """Surface the largest gaps between the model's win probability and the market.

    De-vigs each market's 1X2 decimal odds (removes the margin so implied
    probabilities sum to 1) and compares them to this server's own match-outcome
    probabilities — the same Elo/Poisson path ``football_match_predictor`` uses.
    Where the model probability exceeds the de-vigged market probability by at
    least ``min_edge``, the outcome is flagged with its edge and the
    model's fair odds.

    Args:
        team: Optional team name to filter events (case-insensitive substring,
            matched against both sides). Omit to scan every WC 2026 odds event.
        min_edge: Minimum edge (model_prob - devigged_market_prob), 0..1.
            Default 0.05 (5 percentage points).

    Returns:
        data.value_bets: list of {event_id, home, away, outcome, model_prob,
            fair_odds, market_odds, edge, bookmaker}, sorted by edge descending.
        data.events_analysed: events with both teams rated (model-comparable).
        meta.estimated: true. meta.is_stale reflects the odds freshness.
    """
    if not 0.0 <= min_edge <= 1.0:
        return error_envelope(code="INVALID_INPUT", message="min_edge must be in [0, 1].")

    # Independent chains — fetch concurrently (one round-trip on a cold cache).
    odds_r, groups_r = await asyncio.gather(
        football_odds_chain.fetch(), _groups_payload(), return_exceptions=True
    )
    if isinstance(odds_r, (AllSourcesFailedError, NotFoundError)):
        return error_envelope(
            code=odds_r.code,
            message="No football odds source is available right now.",
            sources_tried=odds_r.attempts,
            suggestion="Set THEODDS_KEY to enable live odds.",
        )
    if isinstance(odds_r, BaseException):
        raise odds_r
    if isinstance(groups_r, (AllSourcesFailedError, NotFoundError)):
        return error_envelope(code=groups_r.code, message="Could not load ratings.", sources_tried=groups_r.attempts)
    if isinstance(groups_r, BaseException):
        raise groups_r
    odds_result, groups_result = odds_r, groups_r

    ratings = groups_result.value.get("ratings", {})
    # Opt-in: nudge the seed forward from live results so value bets compare the
    # market against the same in-tournament form as football_match_predictor.
    ratings, live_elo = await _maybe_nudge_single(groups_result.value, ratings)
    # Odds carry full team names; ratings are keyed by code. Map name -> code from
    # the same draw payload (reusing the seed, not re-deriving any ratings/xG).
    name_to_code = {
        meta.get("name", "").lower(): code
        for code, meta in groups_result.value.get("teams", {}).items()
    }

    events = odds_result.value.get("events", [])
    if team and team.strip():
        q = team.strip().lower()
        events = [e for e in events if q in e.get("home", "").lower() or q in e.get("away", "").lower()]

    value_bets: list[dict] = []
    analysed = 0
    for ev in events:
        home_code = name_to_code.get(ev.get("home", "").lower())
        away_code = name_to_code.get(ev.get("away", "").lower())
        if not home_code or not away_code or home_code not in ratings or away_code not in ratings:
            continue
        analysed += 1
        # Neutral venue — World Cup default, matching football_match_predictor.
        lam_h, lam_a = poisson_xg.lambdas_from_elo(ratings[home_code], ratings[away_code], 0.0)
        model_probs = poisson_xg.outcome_probabilities(lam_h, lam_a)
        for bookmaker in ev.get("bookmakers", []):
            for pick in find_value(model_probs, bookmaker, min_edge):
                value_bets.append(
                    {
                        "event_id": ev.get("event_id"),
                        "home": ev.get("home"),
                        "away": ev.get("away"),
                        **pick,
                    }
                )

    value_bets.sort(key=lambda p: p["edge"], reverse=True)
    meta = {
        "source": odds_result.source,
        "estimated": True,
        **staleness_meta(odds_result),
    }
    if live_elo:
        meta["live_elo"] = True
    return {
        "data": {
            "value_bets": value_bets,
            "min_edge": min_edge,
            "events_analysed": analysed,
        },
        "meta": meta,
    }


async def football_form_trends(team: str) -> Envelope:
    """Return rolling form, goal record, and xG trend for a football team.

    Args:
        team: Team name (e.g. "Brazil", "Argentina").

    Returns:
        data: {form_string, wins, draws, losses, goals_scored, goals_conceded,
               xg_for, xg_against, recent_trend, matches_analysed}.
        meta.estimated: true — derived from available fixture data.
    """
    if not team or not team.strip():
        return error_envelope(code="INVALID_INPUT", message="team must be a non-empty string.")

    try:
        result = await football_fixtures_chain.fetch()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(
            code=e.code,
            message="No fixture source is available right now.",
            sources_tried=e.attempts,
        )

    fixtures = result.value.get("fixtures", [])
    trends = compute_form_trends(fixtures, team)

    meta: dict = {
        "source": result.source,
        "estimated": True,
        **staleness_meta(result),
    }
    if trends["matches_analysed"] == 0:
        meta["note"] = "No completed fixtures found for this team."

    return {"data": trends, "meta": meta}


async def football_build_accumulator(legs: int = 3, min_edge: float = 0.05) -> Envelope:
    """Model the joint probability of several match outcomes from the top model-vs-market gaps.

    Calls ``football_find_value_bets`` internally to fetch live odds, then selects
    the strongest legs and combines them under the joint-probability model.

    Args:
        legs: Number of legs (2-8). Default 3.
        min_edge: Minimum edge threshold per leg. Default 0.05.

    Returns:
        data: {legs, legs_used, combined_odds, combined_model_prob, combined_edge,
               risk_flag, independence_warning}.
        meta.estimated: true.
    """
    if not (2 <= legs <= 8):
        return error_envelope(code="INVALID_INPUT", message="legs must be between 2 and 8 inclusive.")
    if not (0.0 < min_edge < 1.0):
        return error_envelope(code="INVALID_INPUT", message="min_edge must be in (0, 1) exclusive.")

    result = await football_find_value_bets(min_edge=min_edge)

    if result.get("error"):
        return result

    picks = result.get("data", {}).get("value_bets", [])
    acca = build_accumulator(picks, legs=legs, min_edge=min_edge)

    upstream_meta = result.get("meta", {})
    return {
        "data": acca,
        "meta": {
            "source": "derived",
            "is_stale": upstream_meta.get("is_stale", False),
            "data_age_seconds": upstream_meta.get("data_age_seconds", 0),
            "fallback_used": upstream_meta.get("fallback_used", False),
            "duration_ms": upstream_meta.get("duration_ms", 0),
            "estimated": True,
        },
    }


def register_football_intel_tools(mcp) -> None:
    """Register the football INTEL tools on the supplied FastMCP instance."""
    from sportiq.core.tool_meta import READ_ONLY

    mcp.tool(annotations=READ_ONLY)(football_xg_model)
    mcp.tool(annotations=READ_ONLY)(football_match_predictor)
    mcp.tool(annotations=READ_ONLY)(football_simulate_group)
    mcp.tool(annotations=READ_ONLY)(football_simulate_bracket)
    mcp.tool(annotations=READ_ONLY)(football_knockout_path)
    mcp.tool(annotations=READ_ONLY)(football_find_value_bets)
    mcp.tool(annotations=READ_ONLY)(football_form_trends)
    mcp.tool(annotations=READ_ONLY)(football_build_accumulator)
