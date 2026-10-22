"""Football INTEL tools — Phase 4 flagship layer.

Five tools composing the static draw + Elo ratings with the Poisson/Monte-Carlo
models. Flagship: football_simulate_bracket. All route through
football_groups_chain (the source of the draw + ratings) and surface is_stale.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Literal

from sportiq import __version__
from sportiq.config import settings
from sportiq.core.cache import get_cache
from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.core.fallback import FallbackResult
from sportiq.core.logging import get_logger
from sportiq.core.parlay import build_accumulator
from sportiq.core.tool_response import Envelope, error_envelope, staleness_meta
from sportiq.core.value_bet import has_commenced
from sportiq.football.chains import (
    football_fixtures_chain,
    football_groups_chain,
    football_odds_chain,
)
from sportiq.football.models import poisson_xg
from sportiq.football.models.bracket_sim import (
    DEFAULT_RATING,
    simulate_tournament,
    tournament_from_results,
)
from sportiq.football.models.elo_live import nudge_ratings
from sportiq.football.models.form_trends import compute_form_trends
from sportiq.football.models.group_sim import simulate_group_stage
from sportiq.football.models.results_state import (
    REPLAY_STAGES,
    ResultsState,
    build_code_index,
    build_results_state,
    flip_knockout_winner,
    resolve_code,
    results_complete_before,
    truncate_results_state,
)
from sportiq.football.models.value_bet import find_value

_log = get_logger("football.intel")

_MAX_ITERATIONS = 20000
_MIN_ITERATIONS = 100
# Seeded bracket sims are deterministic for fixed inputs, so their output is memoised.
_SIMMEMO_TTL_S = 6 * 3600

_NO_LIVE_NOTE = "Live results unavailable; simulated from the pre-tournament seed."
_TIEBREAK_POLICY = (
    "FIFA 2026 available fields; model rating substitutes for missing conduct/FIFA ranking."
)
_PRIOR_NOTE = (
    "No completed-result evidence was available; this is a reconstructed "
    "pre-tournament simulation, not the current state."
)
_DEFAULT_RATING_NOTE = (
    f"Some entrants have no seed rating and use the default {DEFAULT_RATING:g} "
    "(see meta.default_rating_teams)."
)


async def _groups_payload() -> dict:
    """Fetch the draw + ratings, or raise AllSourcesFailedError."""
    return await football_groups_chain.fetch()


def _resolve_team(value: str, teams_meta: dict) -> str | None:
    """Map a FIFA code, team name or alias ("South Korea") to the draw's team code."""
    code = value.strip().upper()
    if code in teams_meta:
        return code
    return resolve_code(value, build_code_index(teams_meta))


def _seed_ratings(groups_value: dict) -> dict:
    """The seed ratings, plus key aliases where the draw and the seed spell a code differently."""
    ratings = dict(groups_value.get("ratings", {}))
    # label alias only; seed values unchanged (frozen)
    if "KSA" not in ratings and "SAU" in ratings:
        ratings["KSA"] = ratings["SAU"]
    return ratings


def _entrants(groups_value: dict) -> set[str]:
    """Team codes in the draw: the participation check (never the ratings dict)."""
    teams = groups_value.get("teams") or {}
    if teams:
        return set(teams)
    return {code for codes in groups_value.get("groups", {}).values() for code in codes}


def _not_entrant(team: str) -> Envelope:
    return error_envelope(
        code="NOT_FOUND",
        message=f"{team.strip()!r} is not a World Cup 2026 entrant; see football_get_groups.",
    )


def _with_default_ratings(ratings: dict, codes) -> tuple[dict, list[str]]:
    """Fill DEFAULT_RATING for unrated ``codes``; return (ratings, sorted defaulted codes)."""
    missing = sorted({code for code in codes if code not in ratings})
    if not missing:
        return ratings, []
    return {**ratings, **dict.fromkeys(missing, DEFAULT_RATING)}, missing


def _add_note(meta: dict, note: str) -> None:
    meta["note"] = f"{meta['note']} {note}" if meta.get("note") else note


def _disclose_default_ratings(meta: dict, defaulted: list[str]) -> None:
    if defaulted:
        meta["default_rating_teams"] = defaulted
        _add_note(meta, _DEFAULT_RATING_NOTE)


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


def _results_fingerprint(state: ResultsState | None) -> dict | None:
    """Order-independent summary of the locked results (the memo key's results part)."""
    if state is None:
        return None
    return {
        "groups": {
            letter: sorted([list(match) for match in g.completed])
            for letter, g in sorted(state.groups.items())
        },
        "knockout": sorted([list(tie) for tie in state.knockout]),
        "champion": state.champion,
    }


def _simmemo_key(
    groups: dict, ratings: dict, n_iter: int, seed: int, state: ResultsState | None
) -> str:
    payload = json.dumps(
        {
            "groups": groups,
            "results": _results_fingerprint(state),
            "ratings": ratings,
            "n_iter": n_iter,
            "seed": seed,
            "version": __version__,
        },
        sort_keys=True,
    )
    digest = hashlib.blake2s(payload.encode(), digest_size=8).hexdigest()
    return f"sportiq:football:simmemo:{digest}"


async def _run_bracket_sim(
    groups: dict, ratings: dict, n_iter: int, seed: int | None, state: ResultsState | None
) -> dict:
    """Run the bracket Monte Carlo off the event loop, memoising seeded runs.

    Unseeded runs are never memoised (each call is a fresh sample). Cache errors
    fail open: the sim still runs and its result is returned.
    """
    key = _simmemo_key(groups, ratings, n_iter, seed, state) if seed is not None else None
    if key is not None:
        try:
            hit = await get_cache().get(key)
        except Exception as e:
            _log.warning("football.simmemo.read_failed", error=type(e).__name__)
            hit = None
        if hit is not None:
            return hit.value
    sim = await asyncio.to_thread(
        simulate_tournament, groups, ratings, n_iter=n_iter, seed=seed, results=state
    )
    if key is not None:
        try:
            await get_cache().set(key, sim, ttl_seconds=_SIMMEMO_TTL_S)
        except Exception as e:
            _log.warning("football.simmemo.write_failed", error=type(e).__name__)
    return sim


def _exact_if_completed(groups: dict, fixtures_result, state: ResultsState | None) -> dict | None:
    """The locked tournament as exact 1.0/0.0 rounds when every result is in, else None."""
    if state is None or _sim_mode(fixtures_result, state) != "completed":
        return None
    return tournament_from_results(groups, state)


async def _maybe_nudge_single(
    groups_value: dict, ratings: dict
) -> tuple[dict, bool, FallbackResult | None]:
    """For single-match tools: nudge ratings from live results when enabled.

    Returns ``(ratings, live_elo_applied, fixtures_result)``. ``fixtures_result``
    is None when live Elo is off (or no fixture source answered); otherwise the
    caller MUST pass it to ``staleness_meta`` so its freshness is not swallowed.
    No conditioning structure is needed here — these tools score one matchup,
    so only the rating shift matters.
    """
    if not settings.football_live_elo:
        return ratings, False, None
    state, fixtures_result = await _fetch_live_state(groups_value)
    if state is None:
        return ratings, False, fixtures_result
    return nudge_ratings(ratings, state.completed_chrono), True, fixtures_result


def _sim_mode(fixtures_result, state: ResultsState | None) -> str:
    """``completed`` | ``in_progress`` | ``pre_tournament_prior`` for a conditioned sim."""
    if (
        state is None
        or state.matched == 0
        or getattr(fixtures_result, "source", None) == "static_seed"
    ):
        return "pre_tournament_prior"
    if state.champion is not None:
        return "completed"
    return "in_progress"


def _sim_meta(
    groups_result,
    fixtures_result,
    state: ResultsState | None,
    tiebreak_fallbacks: int | None = None,
    default_rating_teams: list[str] | None = None,
) -> dict:
    """Build the meta envelope for a conditioned simulation tool."""
    sources = [groups_result] + ([fixtures_result] if fixtures_result is not None else [])
    mode = _sim_mode(fixtures_result, state)
    meta: dict = {
        "source": groups_result.source,
        "estimated": True,
        "mode": mode,
        "conditioned_matches": state.matched if state else 0,
        **staleness_meta(*sources),
    }
    if mode == "completed":
        meta["champion"] = state.champion
    if state and state.dropped:
        meta["fixtures_dropped"] = state.dropped
    if settings.football_live_elo and state is not None:
        meta["live_elo"] = True
    if state is None:
        meta["note"] = _NO_LIVE_NOTE
    if mode == "pre_tournament_prior":
        _add_note(meta, _PRIOR_NOTE)
    if tiebreak_fallbacks is not None:
        meta["tiebreak_fallbacks"] = tiebreak_fallbacks
        meta["tiebreak_policy"] = _TIEBREAK_POLICY
    _disclose_default_ratings(meta, default_rating_teams or [])
    return meta


async def football_xg_model(home_team: str, away_team: str, neutral: bool = True) -> Envelope:
    """Estimate a match's expected goals and win/draw/loss probabilities.

    Args:
        home_team: First team, FIFA code or name (e.g. "ARG" or "Argentina").
        away_team: Second team, FIFA code or name (e.g. "BRA" or "Brazil").
        neutral: True for a neutral venue (no home advantage). World Cup default.

    Returns:
        data: {expected_home_goals, expected_away_goals, home_win, draw, away_win}.
        meta.estimated: true.
    """
    home, away = home_team.strip().upper(), away_team.strip().upper()
    if not home or not away:
        return error_envelope(
            code="INVALID_INPUT", message="home_team and away_team must be non-empty."
        )
    if len(home) > 100:
        return error_envelope(
            code="INVALID_INPUT", message="home_team must not exceed 100 characters."
        )
    if len(away) > 100:
        return error_envelope(
            code="INVALID_INPUT", message="away_team must not exceed 100 characters."
        )
    if home == away:
        return error_envelope(code="INVALID_INPUT", message="home_team and away_team must differ.")

    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(
            code=e.code, message="Could not load ratings.", sources_tried=e.attempts
        )

    teams_meta = result.value.get("teams", {})
    home = _resolve_team(home_team, teams_meta) or home
    away = _resolve_team(away_team, teams_meta) or away
    if home == away:
        return error_envelope(code="INVALID_INPUT", message="home_team and away_team must differ.")
    entrants = _entrants(result.value)
    for team_code, raw in ((home, home_team), (away, away_team)):
        if team_code not in entrants:
            return _not_entrant(raw)
    ratings, defaulted = _with_default_ratings(_seed_ratings(result.value), (home, away))
    ratings, live_elo, fixtures_result = await _maybe_nudge_single(result.value, ratings)

    home_adv = 0.0 if neutral else 60.0
    lam_h, lam_a = poisson_xg.lambdas_from_elo(ratings[home], ratings[away], home_adv)
    outcome = poisson_xg.outcome_probabilities(lam_h, lam_a)
    freshness = (result, fixtures_result) if fixtures_result is not None else (result,)
    meta = {"source": result.source, "estimated": True, **staleness_meta(*freshness)}
    if live_elo:
        meta["live_elo"] = True
    _disclose_default_ratings(meta, defaulted)
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


async def football_match_predictor(
    home_team: str, away_team: str, neutral: bool = True
) -> Envelope:
    """Predict a single match: most likely scoreline + outcome probabilities.

    Args:
        home_team: First team, FIFA code or name (e.g. "ESP" or "Spain").
        away_team: Second team, FIFA code or name.
        neutral: True for a neutral venue (World Cup default).

    Returns:
        data: {most_likely_score, home_win, draw, away_win, predicted_winner}.
        meta.estimated: true.
    """
    home, away = home_team.strip().upper(), away_team.strip().upper()
    if not home or not away:
        return error_envelope(
            code="INVALID_INPUT", message="home_team and away_team must be non-empty."
        )
    if len(home) > 100:
        return error_envelope(
            code="INVALID_INPUT", message="home_team must not exceed 100 characters."
        )
    if len(away) > 100:
        return error_envelope(
            code="INVALID_INPUT", message="away_team must not exceed 100 characters."
        )
    if home == away:
        return error_envelope(code="INVALID_INPUT", message="home_team and away_team must differ.")

    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(
            code=e.code, message="Could not load ratings.", sources_tried=e.attempts
        )

    teams_meta = result.value.get("teams", {})
    home = _resolve_team(home_team, teams_meta) or home
    away = _resolve_team(away_team, teams_meta) or away
    if home == away:
        return error_envelope(code="INVALID_INPUT", message="home_team and away_team must differ.")
    entrants = _entrants(result.value)
    for team_code, raw in ((home, home_team), (away, away_team)):
        if team_code not in entrants:
            return _not_entrant(raw)
    ratings, defaulted = _with_default_ratings(_seed_ratings(result.value), (home, away))
    ratings, live_elo, fixtures_result = await _maybe_nudge_single(result.value, ratings)

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
    freshness = (result, fixtures_result) if fixtures_result is not None else (result,)
    meta = {"source": result.source, "estimated": True, **staleness_meta(*freshness)}
    if live_elo:
        meta["live_elo"] = True
    _disclose_default_ratings(meta, defaulted)
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
    """Monte Carlo one group within the full 12-group qualification context.

    Args:
        group: Group letter A-L (also accepts "Group A").
        iterations: Number of simulations (clamped to 100..20000).

    Returns:
        data.teams: Per-team position probabilities, p_auto_advance,
            p_best_third_advance, truthful combined p_advance, and avg_points.
        data.iterations: iterations actually run.
        meta.estimated: true. meta.conditioned_matches: completed matches locked in.
    """
    key = group.strip().upper().removeprefix("GROUP").strip()  # "Group A" → "A"
    if len(key) != 1:
        return error_envelope(code="INVALID_INPUT", message="group must be one letter from A to L.")

    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(code=e.code, message="Could not load draw.", sources_tried=e.attempts)

    groups = result.value.get("groups", {})
    if key not in groups:
        return error_envelope(code="NOT_FOUND", message=f"Unknown group {group!r}; groups are A-L.")

    state, fixtures_result = await _fetch_live_state(result.value)
    seed, defaulted = _with_default_ratings(_seed_ratings(result.value), _entrants(result.value))
    ratings = _conditioned_ratings(seed, state)
    try:
        sim = await asyncio.to_thread(
            simulate_group_stage,
            groups,
            ratings,
            n_iter=_clamp_iterations(iterations),
            results=state,
        )
    except (ValueError, KeyError) as e:
        return error_envelope(code="INVALID_INPUT", message=f"Invalid simulation input: {e}")
    selected_teams = {team: sim["teams"][team] for team in groups[key]}
    meta = _sim_meta(
        result,
        fixtures_result,
        state,
        tiebreak_fallbacks=sim["tiebreak_fallbacks"],
        default_rating_teams=defaulted,
    )
    if state:  # group-tool count should reflect only this group's locked matches
        known = state.groups.get(key)
        meta["conditioned_matches"] = len(known.completed) if known else 0
    return {
        "data": {
            "group": key,
            "teams": selected_teams,
            "iterations": sim["iterations"],
        },
        "meta": meta,
    }


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
    if seed is not None and not 0 <= seed <= 2**64 - 1:
        return error_envelope(code="INVALID_INPUT", message="seed must be in [0, 2**64 - 1].")

    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(code=e.code, message="Could not load draw.", sources_tried=e.attempts)

    groups = result.value.get("groups", {})
    state, fixtures_result = await _fetch_live_state(result.value)
    seed_ratings, defaulted = _with_default_ratings(
        _seed_ratings(result.value), _entrants(result.value)
    )
    ratings = _conditioned_ratings(seed_ratings, state)
    # Every result locked (the tournament is over): the answer is exact; skip the sim.
    sim = _exact_if_completed(groups, fixtures_result, state)
    if sim is None:
        try:
            sim = await _run_bracket_sim(
                groups, ratings, _clamp_iterations(iterations), seed, state
            )
        except (ValueError, KeyError) as e:
            return error_envelope(code="INVALID_INPUT", message=f"Invalid simulation input: {e}")
    meta = _sim_meta(
        result,
        fixtures_result,
        state,
        tiebreak_fallbacks=sim["tiebreak_fallbacks"],
        default_rating_teams=defaulted,
    )
    meta["iterations"] = sim["iterations"]
    return {"data": sim, "meta": meta}


async def football_knockout_path(
    team: str, iterations: int = 10000, seed: int | None = None
) -> Envelope:
    """Round-by-round survival probabilities for one team in the full sim.

    Args:
        team: FIFA code or name (e.g. "FRA" or "France").
        iterations: Number of tournament simulations (clamped to 100..20000).
        seed: Optional RNG seed.

    Returns:
        data: {team, reach_r32, reach_r16, reach_qf, reach_sf, reach_final, win}.
        meta.estimated: true.
    """
    code = team.strip().upper()
    if not code:
        return error_envelope(code="INVALID_INPUT", message="team must be non-empty.")
    if len(code) > 100:
        return error_envelope(code="INVALID_INPUT", message="team must not exceed 100 characters.")
    if seed is not None and not 0 <= seed <= 2**64 - 1:
        return error_envelope(code="INVALID_INPUT", message="seed must be in [0, 2**64 - 1].")

    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(code=e.code, message="Could not load draw.", sources_tried=e.attempts)

    groups = result.value.get("groups", {})
    code = _resolve_team(team, result.value.get("teams", {})) or code
    entrants = _entrants(result.value)
    if code not in entrants:
        return _not_entrant(team)
    base_ratings, defaulted = _with_default_ratings(_seed_ratings(result.value), entrants)

    state, fixtures_result = await _fetch_live_state(result.value)
    ratings = _conditioned_ratings(base_ratings, state)
    sim = _exact_if_completed(groups, fixtures_result, state)
    if sim is None:
        try:
            sim = await _run_bracket_sim(
                groups, ratings, _clamp_iterations(iterations), seed, state
            )
        except (ValueError, KeyError) as e:
            return error_envelope(code="INVALID_INPUT", message=f"Invalid simulation input: {e}")
    row = sim["teams"].get(code, {})
    meta = _sim_meta(
        result,
        fixtures_result,
        state,
        tiebreak_fallbacks=sim["tiebreak_fallbacks"],
        default_rating_teams=defaulted,
    )
    meta["iterations"] = sim["iterations"]
    return {"data": {"team": code, **row}, "meta": meta}


def _parse_flip(value: str, teams_meta: dict) -> tuple[str, str] | None:
    """Resolve "ESP-ARG" (any order; names allowed) to two draw codes, else None.

    Tries every hyphen as the split point so hyphenated names still resolve.
    """
    for i, ch in enumerate(value):
        if ch != "-":
            continue
        a = _resolve_team(value[:i], teams_meta) if value[:i].strip() else None
        b = _resolve_team(value[i + 1 :], teams_meta) if value[i + 1 :].strip() else None
        if a and b and a != b:
            return a, b
    return None


_STAGE_LABELS = {
    "group": "the group stage",
    "r32": "the round of 32",
    "r16": "the round of 16",
    "qf": "the quarter-finals",
    "sf": "the semi-finals",
    "final": "the final",
}


async def football_what_if(
    replay_from: Literal["group", "r32", "r16", "qf", "sf", "final"] = "group",
    flip_winner_of: str | None = None,
    iterations: int = 10000,
    seed: int | None = None,
) -> Envelope:
    """Replay World Cup 2026 from a chosen stage, optionally flipping one real knockout result.

    Keeps every real result played before ``replay_from`` and Monte-Carlos the
    rest of the tournament from there. ``flip_winner_of`` makes one decided
    knockout tie in the kept results go the other way first.

    Args:
        replay_from: Stage to re-simulate from: "group" (whole tournament, no
            real results kept), "r32", "r16", "qf", "sf" or "final" (keeps every
            result before the final and simulates only the final).
        flip_winner_of: Optional tie to flip, as two FIFA codes or names joined
            by a hyphen in any order (e.g. "ESP-FRA"). It must be a decided
            knockout tie before ``replay_from``.
        iterations: Number of tournament simulations (clamped to 100..20000).
        seed: Optional RNG seed for reproducible output.

    Returns:
        data.teams: {code: {reach_r32, reach_r16, reach_qf, reach_sf, reach_final, win}}
            sorted by win probability descending.
        data.champion: most likely winner. data.iterations: iterations run.
        meta.mode: "what_if". meta.replay_from: the stage. meta.flipped:
            {tie: [code_a, code_b], winner: code} or null. meta.estimated: true.

    Example:
        football_what_if(replay_from="qf")
        football_what_if(replay_from="final", flip_winner_of="ESP-FRA", seed=7)
    """
    if replay_from not in REPLAY_STAGES:
        return error_envelope(
            code="INVALID_INPUT",
            message=f"replay_from must be one of {', '.join(REPLAY_STAGES)}.",
        )
    if seed is not None and not 0 <= seed <= 2**64 - 1:
        return error_envelope(code="INVALID_INPUT", message="seed must be in [0, 2**64 - 1].")
    if flip_winner_of is not None and len(flip_winner_of) > 200:
        return error_envelope(
            code="INVALID_INPUT", message="flip_winner_of must not exceed 200 characters."
        )

    try:
        result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(code=e.code, message="Could not load draw.", sources_tried=e.attempts)

    groups = result.value.get("groups", {})
    teams_meta = result.value.get("teams", {})
    state, fixtures_result = await _fetch_live_state(result.value)
    if state is None and (replay_from != "group" or flip_winner_of):
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"No real results are available to keep before {_STAGE_LABELS[replay_from]}.",
            suggestion='Use replay_from="group" for a full pre-tournament replay.',
        )
    kept = truncate_results_state(state, replay_from) if state is not None else None
    if kept is not None and not results_complete_before(kept, replay_from):
        # e.g. the static fixture fallback: a draw without scores must not be
        # reported as "real results kept".
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=(
                f"The available fixture data does not hold every real result before "
                f"{_STAGE_LABELS[replay_from]}, so they cannot be kept."
            ),
            suggestion='Retry later, or use replay_from="group" for a full pre-tournament replay.',
        )

    flipped: dict | None = None
    if flip_winner_of:
        codes = _parse_flip(flip_winner_of, teams_meta)
        if codes is None:
            return error_envelope(
                code="INVALID_INPUT",
                message=f"Could not read {flip_winner_of!r} as two World Cup teams, e.g. 'ESP-FRA'.",
            )
        try:
            kept = flip_knockout_winner(kept, *codes)
        except ValueError:
            return error_envelope(
                code="INVALID_INPUT",
                message=(
                    f"{codes[0]}-{codes[1]} is not a decided knockout tie before "
                    f"{_STAGE_LABELS[replay_from]}."
                ),
                suggestion="Pick a later replay_from, or a tie that was actually played.",
            )
        winner = next(w for a, b, w in kept.knockout if {a, b} == set(codes))
        flipped = {"tie": list(codes), "winner": winner}

    base_ratings, defaulted = _with_default_ratings(
        _seed_ratings(result.value), _entrants(result.value)
    )
    ratings = _conditioned_ratings(base_ratings, kept)
    try:
        sim = await _run_bracket_sim(groups, ratings, _clamp_iterations(iterations), seed, kept)
    except (ValueError, KeyError) as e:
        return error_envelope(code="INVALID_INPUT", message=f"Invalid simulation input: {e}")

    meta = _sim_meta(result, fixtures_result, kept, tiebreak_fallbacks=sim["tiebreak_fallbacks"])
    meta.pop("champion", None)
    meta["mode"] = "what_if"
    meta["replay_from"] = replay_from
    meta["flipped"] = flipped
    meta["iterations"] = sim["iterations"]
    note = (
        f"What-if replay: real results before {_STAGE_LABELS[replay_from]} are kept; "
        "everything from there on is simulated."
    )
    if flipped:
        note += f" {flipped['tie'][0]}-{flipped['tie'][1]} was flipped to {flipped['winner']}."
    meta["note"] = f"{_NO_LIVE_NOTE} {note}" if state is None else note
    _disclose_default_ratings(meta, defaulted)
    return {"data": sim, "meta": meta}


async def football_find_value_bets(team: str | None = None, min_edge: float = 0.05) -> Envelope:
    """Surface the largest gaps between the model's win probability and the market.

    De-vigs each market's 1X2 decimal odds (removes the margin so implied
    probabilities sum to 1) and compares them to this server's own match-outcome
    probabilities — the same Elo/Poisson path ``football_match_predictor`` uses.
    Flags outcomes where the model beats the de-vigged market by ``min_edge``
    **and** the offered price has positive expected value, with the edge, the
    expected value and the model's fair odds. Events that have already started
    are skipped.

    Args:
        team: Optional FIFA code or team name to filter events (matched against
            both sides; an unrecognised value falls back to a case-insensitive
            substring match). Omit to scan every WC 2026 odds event.
        min_edge: Minimum edge (model_prob - devigged_market_prob), 0..1.
            Default 0.05 (5 percentage points).

    Returns:
        data.value_bets: list of {event_id, home, away, outcome, model_prob,
            fair_odds, market_odds, edge, ev_pct, bookmaker, price_updated_at},
            sorted by edge descending.
        data.events_analysed: not-yet-started events with both teams in the draw.
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
        return error_envelope(
            code=groups_r.code, message="Could not load ratings.", sources_tried=groups_r.attempts
        )
    if isinstance(groups_r, BaseException):
        raise groups_r
    odds_result, groups_result = odds_r, groups_r

    entrants = _entrants(groups_result.value)
    ratings, unrated = _with_default_ratings(_seed_ratings(groups_result.value), entrants)
    # Opt-in: nudge the seed forward from live results so value bets compare the
    # market against the same in-tournament form as football_match_predictor.
    ratings, live_elo, fixtures_result = await _maybe_nudge_single(groups_result.value, ratings)
    # Odds carry full team names; ratings are keyed by code. Resolve names (and
    # aliases like "Korea Republic") -> code from the same draw payload (reusing
    # the seed, not re-deriving any ratings/xG).
    teams_meta = groups_result.value.get("teams", {})
    index = build_code_index(teams_meta)

    events = odds_result.value.get("events", [])
    if team and team.strip():
        wanted = _resolve_team(team, teams_meta)
        if wanted is not None:
            events = [
                e
                for e in events
                if wanted
                in (
                    resolve_code(e.get("home") or "", index),
                    resolve_code(e.get("away") or "", index),
                )
            ]
        else:
            q = team.strip().lower()
            events = [
                e
                for e in events
                if q in (e.get("home") or "").lower() or q in (e.get("away") or "").lower()
            ]

    value_bets: list[dict] = []
    analysed = 0
    defaulted: set[str] = set()
    for ev in events:
        # Started / in-play events are not priced against a pre-match model.
        if has_commenced(ev):
            continue
        home_code = resolve_code(ev.get("home") or "", index)
        away_code = resolve_code(ev.get("away") or "", index)
        if home_code not in entrants or away_code not in entrants:
            continue
        analysed += 1
        defaulted.update(c for c in (home_code, away_code) if c in unrated)
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
        **staleness_meta(
            odds_result,
            groups_result,
            *([fixtures_result] if fixtures_result is not None else []),
        ),
    }
    if live_elo:
        meta["live_elo"] = True
    _disclose_default_ratings(meta, sorted(defaulted))
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
        team: FIFA code (e.g. ARG) or name (e.g. "Argentina", "South Korea").

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

    # The draw's team metadata lets "ARG", "Argentina" and aliases resolve to one
    # code. Best-effort: without it, fall back to plain name matching.
    try:
        groups_result = await _groups_payload()
    except (AllSourcesFailedError, NotFoundError):
        groups_result = None
    teams_meta = groups_result.value.get("teams", {}) if groups_result else {}
    code_index = build_code_index(teams_meta) if teams_meta else None

    fixtures = result.value.get("fixtures", [])
    trends = compute_form_trends(fixtures, team, code_index)

    freshness = (result, groups_result) if groups_result else (result,)
    meta: dict = {
        "source": result.source,
        "estimated": True,
        **staleness_meta(*freshness),
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
        return error_envelope(
            code="INVALID_INPUT", message="legs must be between 2 and 8 inclusive."
        )
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
    mcp.tool(annotations=READ_ONLY)(football_what_if)
    mcp.tool(annotations=READ_ONLY)(football_find_value_bets)
    mcp.tool(annotations=READ_ONLY)(football_form_trends)
    mcp.tool(annotations=READ_ONLY)(football_build_accumulator)
