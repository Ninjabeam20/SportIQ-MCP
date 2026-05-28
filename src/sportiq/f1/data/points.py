"""F1 points tables — race + sprint, plus fastest lap bonus."""
from __future__ import annotations

# Race: positions 1..10 (index 0 = P1)
RACE_POINTS: list[int] = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]

# Fastest lap bonus (only if finishing in top 10)
FASTEST_LAP_BONUS: int = 1

# Sprint race: positions 1..8
SPRINT_POINTS: list[int] = [8, 7, 6, 5, 4, 3, 2, 1]


def race_points_for_position(position: int, fastest_lap: bool = False) -> int:
    """Return championship points for a race finish position (1-indexed).

    Args:
        position: Finishing position, 1-indexed.
        fastest_lap: Whether this driver set the fastest lap.

    Returns:
        Championship points. 0 if outside points positions.
    """
    base = RACE_POINTS[position - 1] if 1 <= position <= len(RACE_POINTS) else 0
    bonus = FASTEST_LAP_BONUS if fastest_lap and 1 <= position <= 10 else 0
    return base + bonus


def sprint_points_for_position(position: int) -> int:
    """Return championship points for a sprint race finish (1-indexed)."""
    return SPRINT_POINTS[position - 1] if 1 <= position <= len(SPRINT_POINTS) else 0
