"""Football INTEL tools — Phase 4 flagship layer.

Five tools composing the static draw + Elo ratings with the Poisson/Monte-Carlo
models. Flagship: football_simulate_bracket. All route through
football_groups_chain (the source of the draw + ratings) and surface is_stale.
"""
from __future__ import annotations

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.tool_response import error_envelope, staleness_meta
from sportiq.football.chains import football_groups_chain
from sportiq.football.models import poisson_xg
from sportiq.football.models.bracket_sim import simulate_tournament
from sportiq.football.models.group_sim import simulate_group as _simulate_group

_MAX_ITERATIONS = 50000
_MIN_ITERATIONS = 100


async def _groups_payload() -> dict:
    """Fetch the draw + ratings, or raise AllSourcesFailedError."""
    return await football_groups_chain.fetch()


def _clamp_iterations(iterations: int) -> int:
    return max(_MIN_ITERATIONS, min(_MAX_ITERATIONS, iterations))


async def football_xg_model(home_team: str, away_team: str, neutral: bool = True) -> dict:
    """Estimate a match's expected goals and win/draw/loss probabilities.

    Args:
        home_team: First team code (e.g. "ARG").
        away_team: Second team code (e.g. "BRA").
        neutral: True for a neutral venue (no home advantage). World Cup default.

    Returns:
        data: {expected_home_goals, expected_away_goals, home_win, draw, away_win}.
        meta.estimated: true.
    """
    try:
        result = await _groups_payload()
    except AllSourcesFailedError as e:
        return error_envelope(code="ALL_SOURCES_FAILED", message="Could not load ratings.", sources_tried=e.attempts)

    ratings = result.value.get("ratings", {})
    home, away = home_team.upper(), away_team.upper()
    if home not in ratings or away not in ratings:
        return error_envelope(code="NOT_FOUND", message="Unknown team code; see football_get_groups.")

    home_adv = 0.0 if neutral else 60.0
    lam_h, lam_a = poisson_xg.lambdas_from_elo(ratings[home], ratings[away], home_adv)
    outcome = poisson_xg.outcome_probabilities(lam_h, lam_a)
    return {
        "data": {
            "home_team": home,
            "away_team": away,
            "expected_home_goals": round(lam_h, 3),
            "expected_away_goals": round(lam_a, 3),
            **outcome,
        },
        "meta": {"source": result.source, "estimated": True, **staleness_meta(result)},
    }


async def football_match_predictor(home_team: str, away_team: str, neutral: bool = True) -> dict:
    """Predict a single match: most likely scoreline + outcome probabilities.

    Args:
        home_team: First team code.
        away_team: Second team code.
        neutral: True for a neutral venue (World Cup default).

    Returns:
        data: {most_likely_score, home_win, draw, away_win, predicted_winner}.
        meta.estimated: true.
    """
    try:
        result = await _groups_payload()
    except AllSourcesFailedError as e:
        return error_envelope(code="ALL_SOURCES_FAILED", message="Could not load ratings.", sources_tried=e.attempts)

    ratings = result.value.get("ratings", {})
    home, away = home_team.upper(), away_team.upper()
    if home not in ratings or away not in ratings:
        return error_envelope(code="NOT_FOUND", message="Unknown team code; see football_get_groups.")

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
    return {
        "data": {
            "home_team": home,
            "away_team": away,
            "most_likely_score": f"{gh}-{ga}",
            "predicted_winner": winner,
            **outcome,
        },
        "meta": {"source": result.source, "estimated": True, **staleness_meta(result)},
    }


async def football_simulate_group(group: str, iterations: int = 5000) -> dict:
    """Monte Carlo one group's round-robin -> per-team qualification probabilities.

    Args:
        group: Group letter A-L.
        iterations: Number of simulations (clamped to 100..50000).

    Returns:
        data.teams: {code: {p_first, p_second, p_third, p_fourth, p_advance, avg_points}}.
        data.iterations: iterations actually run.
        meta.estimated: true.
    """
    try:
        result = await _groups_payload()
    except AllSourcesFailedError as e:
        return error_envelope(code="ALL_SOURCES_FAILED", message="Could not load draw.", sources_tried=e.attempts)

    groups = result.value.get("groups", {})
    ratings = result.value.get("ratings", {})
    key = group.upper()
    if key not in groups:
        return error_envelope(code="NOT_FOUND", message=f"Unknown group {group!r}; groups are A-L.")

    sim = _simulate_group(groups[key], ratings, n_iter=_clamp_iterations(iterations))
    return {
        "data": {"group": key, **sim},
        "meta": {"source": result.source, "estimated": True, **staleness_meta(result)},
    }


async def football_simulate_bracket(iterations: int = 10000, seed: int | None = None) -> dict:
    """Monte Carlo the full World Cup 2026 — per-team round + title probabilities.

    Simulates all 12 groups, advances the top 2 + 8 best third-placed teams to a
    32-team knockout, and plays it to a champion, ``iterations`` times.

    Args:
        iterations: Number of tournament simulations (clamped to 100..50000;
            ~10000 gives stable ±2% probabilities).
        seed: Optional RNG seed for reproducible output.

    Returns:
        data.teams: {code: {reach_r32, reach_r16, reach_qf, reach_sf, reach_final, win}}
            sorted by win probability descending.
        data.champion: most likely winner.
        data.iterations: iterations run.
        meta.estimated: true.
    """
    try:
        result = await _groups_payload()
    except AllSourcesFailedError as e:
        return error_envelope(code="ALL_SOURCES_FAILED", message="Could not load draw.", sources_tried=e.attempts)

    groups = result.value.get("groups", {})
    ratings = result.value.get("ratings", {})
    sim = simulate_tournament(groups, ratings, n_iter=_clamp_iterations(iterations), seed=seed)
    return {
        "data": sim,
        "meta": {"source": result.source, "estimated": True, **staleness_meta(result)},
    }


async def football_knockout_path(team: str, iterations: int = 10000, seed: int | None = None) -> dict:
    """Round-by-round survival probabilities for one team in the full sim.

    Args:
        team: Team code (e.g. "FRA").
        iterations: Number of tournament simulations (clamped to 100..50000).
        seed: Optional RNG seed.

    Returns:
        data: {team, reach_r32, reach_r16, reach_qf, reach_sf, reach_final, win}.
        meta.estimated: true.
    """
    try:
        result = await _groups_payload()
    except AllSourcesFailedError as e:
        return error_envelope(code="ALL_SOURCES_FAILED", message="Could not load draw.", sources_tried=e.attempts)

    groups = result.value.get("groups", {})
    ratings = result.value.get("ratings", {})
    code = team.upper()
    if code not in ratings:
        return error_envelope(code="NOT_FOUND", message="Unknown team code; see football_get_groups.")

    sim = simulate_tournament(groups, ratings, n_iter=_clamp_iterations(iterations), seed=seed)
    row = sim["teams"].get(code, {})
    return {
        "data": {"team": code, **row},
        "meta": {"source": result.source, "estimated": True, **staleness_meta(result)},
    }


def register_football_intel_tools(mcp) -> None:
    """Register the five football INTEL tools on the supplied FastMCP instance."""
    mcp.tool()(football_xg_model)
    mcp.tool()(football_match_predictor)
    mcp.tool()(football_simulate_group)
    mcp.tool()(football_simulate_bracket)
    mcp.tool()(football_knockout_path)
