"""Synthesise a pitch report from venue characteristics.

For Phase 2 the input is the static venues.json record. The model maps the
pitch_type + first-innings average into a 0..1 batting_friendly score and a
short string recommendation that AI callers can quote directly.
"""

from __future__ import annotations

_PITCH_TYPE_FRIENDLY = {"batting": 0.78, "balanced": 0.55, "bowling": 0.32}


def _avg_factor(avg_first_innings: int) -> float:
    """Normalise first-innings average into a 0..1 batting-friendliness shift.

    A 150 avg → -0.15; a 200 avg → +0.15. Centred at 175 (typical T20 par).
    """
    return max(-0.15, min(0.15, (avg_first_innings - 175) / 200.0))


def pitch_report(venue_record: dict) -> dict:
    """Compose the pitch-friendliness summary used by tools.

    Args:
        venue_record: a row from venues.json (already fetched via
            ``pitch_data_chain``). Must contain ``pitch_type`` and
            ``avg_first_innings``; ``name``/``city`` echoed back if present.

    Returns:
        {
            "batting_friendly": 0..1,
            "expected_first_inn": int,
            "recommendation": str,
            "venue": str,
            "pitch_type": str,
        }
    """
    pitch_type = (venue_record or {}).get("pitch_type", "balanced")
    avg_first = int((venue_record or {}).get("avg_first_innings", 170))
    base = _PITCH_TYPE_FRIENDLY.get(pitch_type, 0.55)
    friendly = max(0.0, min(1.0, base + _avg_factor(avg_first)))

    if friendly >= 0.70:
        recommendation = (
            "High-scoring deck — load up on top-order batters and finishers; "
            "fade specialist seamers in favour of wicket-taking spinners."
        )
    elif friendly <= 0.40:
        recommendation = (
            "Bowler-friendly track — stack pace + wrist-spin wickets; "
            "trim the batting lineup to anchor types over hitters."
        )
    else:
        recommendation = (
            "Balanced pitch — pick top-order anchors plus a wicket-taker. "
            "No structural tilt; lean on form."
        )

    return {
        "batting_friendly": round(friendly, 3),
        "expected_first_inn": avg_first,
        "recommendation": recommendation,
        "venue": (venue_record or {}).get("name") or (venue_record or {}).get("key"),
        "pitch_type": pitch_type,
    }
