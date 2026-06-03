"""Heuristic pre-match T20 win probability.

Pure function — no I/O. All signal values are optional (default 0.5 = neutral)
so the model degrades gracefully when data is unavailable. T20 has no draw,
so probabilities sum to 1 across two outcomes only.

Inputs (both dicts with the same keys):
  form_score: float 0-100 (from form_index model). Default 50 (neutral).
  h2h_win_rate: float 0-1 (fraction of H2H wins). Default 0.5 (no history).
  venue_tilt: float 0-1 (batting_friendly from pitch_report; 0.5 = balanced).

Signal weighting (calibrated for T20):
  form  → 50%
  h2h   → 30%
  venue → 20% (as an advantage offset — team_a gets +tilt, team_b gets +(1-tilt))
"""

from __future__ import annotations

_WEIGHTS = {"form": 0.5, "h2h": 0.3, "venue": 0.2}


def _normalise_form(score: float) -> float:
    """Map form_score 0-100 → 0-1."""
    return max(0.0, min(1.0, score / 100.0))


def win_prob(
    team_a_signals: dict,
    team_b_signals: dict,
) -> dict[str, float]:
    """Estimate pre-match T20 win probabilities for two teams.

    Args:
        team_a_signals: dict with optional keys: form_score (0-100),
            h2h_win_rate (0-1), venue_tilt (0-1).
        team_b_signals: same structure.

    Returns:
        {"team_a": float, "team_b": float} summing to 1.0.
    """
    a_form = _normalise_form(team_a_signals.get("form_score", 50.0))
    b_form = _normalise_form(team_b_signals.get("form_score", 50.0))
    form_sum = a_form + b_form
    a_form_p = a_form / form_sum if form_sum > 0 else 0.5

    a_h2h = float(team_a_signals.get("h2h_win_rate", 0.5))
    b_h2h = 1.0 - float(team_b_signals.get("h2h_win_rate", 1.0 - a_h2h))

    venue_tilt = float(team_a_signals.get("venue_tilt", 0.5))
    a_venue = venue_tilt
    b_venue = 1.0 - venue_tilt

    a_raw = (
        _WEIGHTS["form"] * a_form_p
        + _WEIGHTS["h2h"] * a_h2h
        + _WEIGHTS["venue"] * a_venue
    )
    b_raw = (
        _WEIGHTS["form"] * (1.0 - a_form_p)
        + _WEIGHTS["h2h"] * b_h2h
        + _WEIGHTS["venue"] * b_venue
    )
    total = a_raw + b_raw
    if total == 0:
        return {"team_a": 0.5, "team_b": 0.5}
    return {
        "team_a": round(a_raw / total, 4),
        "team_b": round(b_raw / total, 4),
    }
