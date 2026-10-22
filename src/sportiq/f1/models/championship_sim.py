"""F1 drivers' title-race Monte Carlo + exact elimination maths (pure, no I/O).

Strength model: each driver's points rate (season points / rounds completed,
floored at 0.5). Every remaining race (and sprint) samples a full finishing
order by Plackett-Luce with weights ``strength ** 1.5``, vectorised with the
Gumbel-max trick: ``argsort(log w + Gumbel)`` is an exact Plackett-Luce draw.
Points come from ``f1/data/points.py``. Fastest-lap points are not sampled
(they only exist before 2025); ``max_remaining_points`` still counts them so
elimination stays conservative.

Elimination is exact, never sampled: a driver whose ``points_now +
max_remaining`` is below the leader's current points cannot win, so
``title_prob`` is 0.0 regardless of the simulation.
"""

from __future__ import annotations

import numpy as np

from sportiq.f1.data.points import (
    RACE_POINTS,
    SPRINT_POINTS,
    race_points_for_position,
    sprint_points_for_position,
)

_STRENGTH_FLOOR = 0.5
_PL_EXPONENT = 1.5


def max_remaining_points(remaining: list[dict], year: int) -> int:
    """Most points one driver can still score: race P1 (+ sprint P1) per remaining round.

    Args:
        remaining: rounds still to run, ``[{"round": int, "sprint": bool}]``.
        year: season; the fastest-lap point counts only before 2025.
    """
    race_max = race_points_for_position(1, fastest_lap=True, year=year)
    sprint_max = sprint_points_for_position(1)
    return sum(race_max + (sprint_max if r.get("sprint") else 0) for r in remaining)


def _points_table(table: list[int], n_drivers: int) -> np.ndarray:
    out = np.zeros(n_drivers)
    k = min(len(table), n_drivers)
    out[:k] = table[:k]
    return out


def simulate_championship(
    standings: list[dict],
    remaining: list[dict],
    *,
    year: int,
    n_iter: int,
    seed: int | None,
    rounds_completed: int | None = None,
) -> dict:
    """Simulate the rest of the season and return per-driver title probabilities.

    Args:
        standings: driver rows in the normalised standings shape
            (``{"code", "points", ...}``).
        remaining: rounds still to run, ``[{"round": int, "sprint": bool}]``.
        year: season (points rules).
        n_iter: Monte Carlo iterations.
        seed: RNG seed for reproducible results (None = random).
        rounds_completed: rounds counted in ``standings`` (strength denominator);
            defaults to 1 when unknown. Plackett-Luce is scale-invariant, so this
            only moves where the 0.5 strength floor applies.
    """
    codes = [str(row.get("code") or "") for row in standings]
    points_now = np.array([float(row.get("points") or 0.0) for row in standings])
    n = len(codes)
    max_rem = max_remaining_points(remaining, year)
    if n == 0:
        return {"drivers": [], "max_remaining_points": max_rem, "rounds_remaining": len(remaining)}

    done = max(1, int(rounds_completed or 1))
    strength = np.maximum(points_now / done, _STRENGTH_FLOOR)
    log_w = _PL_EXPONENT * np.log(strength)

    rng = np.random.default_rng(seed)
    race_pts = _points_table(RACE_POINTS, n)
    sprint_pts = _points_table(SPRINT_POINTS, n)
    gained = np.zeros((n_iter, n))
    for rnd in remaining:
        tables = [race_pts, sprint_pts] if rnd.get("sprint") else [race_pts]
        for table in tables:
            keys = log_w + rng.gumbel(size=(n_iter, n))
            order = np.argsort(-keys, axis=1)  # order[i, pos] = driver index
            np.put_along_axis(
                gained, order, np.take_along_axis(gained, order, axis=1) + table, axis=1
            )

    final = points_now + gained
    # Random tie-break among equal totals (countback is not modelled).
    jitter = rng.random(size=final.shape) * 1e-6
    winners = np.argmax(final + jitter, axis=1)
    title_prob = np.bincount(winners, minlength=n) / n_iter

    leader_now = float(points_now.max())
    eliminated = points_now + max_rem < leader_now
    title_prob = np.where(eliminated, 0.0, title_prob)
    total = title_prob.sum()
    if total > 0:
        title_prob = title_prob / total

    expected = final.mean(axis=0)
    drivers = [
        {
            "code": codes[i],
            "points_now": float(points_now[i]),
            "title_prob": round(float(title_prob[i]), 4),
            "expected_points": round(float(expected[i]), 1),
            "eliminated": bool(eliminated[i]),
            "max_possible": float(points_now[i] + max_rem),
        }
        for i in range(n)
    ]
    drivers.sort(key=lambda d: (-d["title_prob"], -d["points_now"]))
    return {
        "drivers": drivers,
        "max_remaining_points": max_rem,
        "rounds_remaining": len(remaining),
    }
