"""Form index - 0-100 score combining recent innings + career baseline.

Recent innings are weighted exponentially (newest first); the career baseline
provides a regression target. Trend is read off the last-vs-rest delta.
"""

from __future__ import annotations

from collections.abc import Iterable

# Weight applied to each of the last N=5 innings, newest first. Sum to 1.0
# so the recent component stays comparable to the career baseline.
_RECENT_WEIGHTS = (0.40, 0.25, 0.15, 0.12, 0.08)

# Weight given to the recent block vs the career baseline. 0.7 means recent
# form dominates but a deep career still pulls a slumping star upward.
_RECENT_VS_CAREER = 0.7


def _innings_score(inn: dict) -> float:
    """Map one innings into a 0..100ish point estimate.

    Combines runs (linear), strike-rate (bonus), and a small wicket credit
    for bowlers. Calibration: a 50 off 30 with no wickets scores ~80; a
    100 not out scores ~150 (then capped); a 0-ball duck scores 0.
    """
    runs = float(inn.get("runs", 0) or 0)
    balls = float(inn.get("balls", 0) or 0)
    wickets = float(inn.get("wickets", 0) or 0)
    if balls > 0:
        sr = (runs / balls) * 100
        sr_bonus = max(0.0, min(40.0, (sr - 100.0) * 0.4))
    else:
        sr_bonus = 0.0
    bowling_credit = wickets * 20.0
    return runs + sr_bonus + bowling_credit


def _weighted_recent(innings: list[dict]) -> tuple[float, int]:
    """Apply _RECENT_WEIGHTS to up to len(_RECENT_WEIGHTS) newest innings."""
    if not innings:
        return 0.0, 0
    sample = innings[: len(_RECENT_WEIGHTS)]
    weights = _RECENT_WEIGHTS[: len(sample)]
    weight_total = sum(weights)
    scaled = sum(_innings_score(inn) * w for inn, w in zip(sample, weights, strict=False))
    return scaled / weight_total, len(sample)


def _career_baseline(career_avg: float, career_sr: float) -> float:
    """A coarse 0..100ish baseline from career batting numbers."""
    avg_part = max(0.0, min(60.0, career_avg))            # 0..60 → 0..60
    sr_part = max(0.0, min(40.0, (career_sr - 100.0) * 0.4))  # SR 100..200 → 0..40
    return avg_part + sr_part


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def compute_form_index(
    recent_innings: list[dict],
    career_avg: float,
    career_sr: float,
) -> dict:
    """Return a form snapshot for the player.

    Args:
        recent_innings: newest-first list of dicts with at minimum
            ``runs`` and ``balls`` keys; ``wickets`` adds bowler credit.
        career_avg: career batting average (T20 preferred).
        career_sr: career strike rate.

    Returns:
        {"form_score": 0..100, "trend": "rising|stable|falling", "samples": N}
    """
    recent_score, samples = _weighted_recent(recent_innings)
    baseline = _career_baseline(career_avg or 0.0, career_sr or 0.0)

    if samples == 0:
        # No recent data — fall back fully to career.
        return {"form_score": _clamp(baseline), "trend": "stable", "samples": 0}

    blended = _RECENT_VS_CAREER * recent_score + (1 - _RECENT_VS_CAREER) * baseline
    score = _clamp(blended)

    # Trend: compare the latest innings to the median of the rest.
    trend = "stable"
    if samples >= 2:
        latest = _innings_score(recent_innings[0])
        rest: Iterable[dict] = recent_innings[1:samples]
        rest_scores = sorted(_innings_score(i) for i in rest)
        rest_median = rest_scores[len(rest_scores) // 2]
        if latest > rest_median * 1.2:
            trend = "rising"
        elif latest < rest_median * 0.8:
            trend = "falling"

    return {"form_score": score, "trend": trend, "samples": samples}


def player_form_index(raw_stats: dict) -> dict:
    """Derive a form snapshot from a raw player-stats payload (no I/O).

    Handles CricAPI ``data.stats`` and RapidAPI Cricbuzz ``values`` shapes.
    Falls back to neutral (form_score=50, trend='stable') when the payload
    carries no recognisable career numbers.

    Args:
        raw_stats: upstream stats dict as returned by ``player_stats_chain``.

    Returns:
        {"form_score": 0..100, "trend": "rising|stable|falling", "samples": N}
    """
    avg, sr = 0.0, 0.0

    # CricAPI shape: raw_stats["data"]["stats"] list
    cric_rows = (raw_stats or {}).get("data", {}).get("stats", [])
    if cric_rows:
        for row in cric_rows:
            if row.get("matchtype") != "t20i" or row.get("fn") != "batting":
                continue
            try:
                if row.get("stat") == "Average":
                    avg = float(row.get("value", 0) or 0)
                elif row.get("stat") == "Strike Rate":
                    sr = float(row.get("value", 0) or 0)
            except (TypeError, ValueError):
                continue

    # RapidAPI Cricbuzz shape: raw_stats["values"] list
    if not avg and not sr:
        for row in (raw_stats or {}).get("values", []):
            if row.get("name") != "T20I":
                continue
            try:
                avg = float(row.get("average", 0) or 0)
                sr = float(row.get("strikeRate", 0) or 0)
            except (TypeError, ValueError):
                pass
            break

    # recent_innings not available from career-stats endpoints; fall back fully
    # to the career baseline (compute_form_index handles samples=0 gracefully).
    return compute_form_index([], career_avg=avg, career_sr=sr)
