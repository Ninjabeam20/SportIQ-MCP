"""In-tournament Elo nudging — walk the frozen seed forward from real results.

Pure functions, no I/O. The shipped ``elo_seed.json`` is frozen pre-tournament;
this applies the completed WC matches on top of it (standard Elo update) so the
*unplayed* matches the simulators still sample, and the single-match predictors,
reflect current form. It never rewrites the seed file.

Interaction with result-conditioning: the sims already LOCK played group matches
at their real scores, so the nudge does not double-count them — it only changes
the rating used to sample matches that haven't happened yet. ``football_match_predictor``
and ``football_xg_model`` do not condition, so the nudge is the only path by
which form enters those tools.

Off by default; gated behind ``settings.football_live_elo``
(``SPORTIQ_FOOTBALL_LIVE_ELO=1``). The K-factor is the international default;
this deliberately does NOT re-tune the seed lineage (see project D1 finding).
"""
from __future__ import annotations

from sportiq.football.models.elo import expected_score, update_rating

_DEFAULT_RATING = 1500.0
_K = 30.0


def nudge_ratings(
    seed_ratings: dict[str, float],
    completed_matches: list[tuple[str, str, int, int]],
    *,
    enabled: bool = True,
    k: float = _K,
) -> dict[str, float]:
    """Return ratings adjusted by completed matches (neutral venue, chronological).

    Args:
        seed_ratings: ``{code: elo}`` frozen seed (not mutated).
        completed_matches: ``(code_a, code_b, goals_a, goals_b)`` in date order,
            e.g. ``ResultsState.completed_chrono``.
        enabled: when False, returns a copy of the seed unchanged (toggle off).
        k: Elo K-factor.

    Returns:
        A new ratings dict. Teams absent from the seed start at 1500.
    """
    ratings = dict(seed_ratings)
    if not enabled:
        return ratings

    for a, b, ga, gb in completed_matches:
        ra = ratings.get(a, _DEFAULT_RATING)
        rb = ratings.get(b, _DEFAULT_RATING)
        exp_a = expected_score(ra, rb)
        if ga > gb:
            actual_a = 1.0
        elif ga < gb:
            actual_a = 0.0
        else:
            actual_a = 0.5
        ratings[a] = update_rating(ra, exp_a, actual_a, k)
        ratings[b] = update_rating(rb, 1.0 - exp_a, 1.0 - actual_a, k)
    return ratings
