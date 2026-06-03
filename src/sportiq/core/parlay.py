"""Parlay / accumulator builder — pure functions, no I/O.

Takes a list of value-bet picks (each with ``edge``, ``decimal_odds``,
``model_prob``, and a match identifier) and selects the best legs for an
accumulator bet, computing combined odds, combined model probability, and
combined edge under the independence assumption.

Usage::

    from sportiq.core.parlay import build_accumulator
    acca = build_accumulator(picks, legs=3, min_edge=0.05)
"""
from __future__ import annotations

import math


def build_accumulator(
    picks: list[dict],
    legs: int = 3,
    min_edge: float = 0.05,
) -> dict:
    """Build an accumulator from a list of value-bet picks.

    Steps:
    1. Filter to picks with ``edge >= min_edge``.
    2. Deduplicate to one pick per match (keep highest-edge pick per match).
    3. Sort descending by edge; take the top ``legs``.
    4. Compute combined odds, combined model probability, and combined edge.

    Args:
        picks: List of pick dicts. Each must have ``edge`` (float),
            ``decimal_odds`` / ``market_odds`` (float), ``model_prob`` (float),
            and a match identifier field (``match_id`` or ``event_id``).
        legs: Number of legs to select.
        min_edge: Minimum edge threshold per leg.

    Returns:
        dict with keys: ``legs`` (selected picks), ``legs_used``,
        ``combined_odds``, ``combined_model_prob``, ``combined_edge``,
        ``risk_flag``, ``independence_warning``.
    """
    # 1. Filter by min_edge
    qualified = [p for p in picks if p.get("edge", 0.0) >= min_edge]

    # 2. Deduplicate: one pick per match (highest edge wins)
    seen: dict[str, dict] = {}
    for pick in qualified:
        mid = str(pick.get("match_id") or pick.get("event_id") or id(pick))
        if mid not in seen or pick.get("edge", 0.0) > seen[mid].get("edge", 0.0):
            seen[mid] = pick
    deduped = list(seen.values())

    # 3. Sort descending by edge, take top `legs`
    deduped.sort(key=lambda p: p.get("edge", 0.0), reverse=True)
    selected = deduped[:legs]

    legs_used = len(selected)

    if legs_used == 0:
        return {
            "legs": [],
            "legs_used": 0,
            "combined_odds": 1.0,
            "combined_model_prob": 1.0,
            "combined_edge": 0.0,
            "risk_flag": False,
            "independence_warning": (
                "Probabilities multiplied under independence assumption. "
                "Legs are from different matches."
            ),
        }

    # 4. Compute combined statistics
    # Picks from football_find_value_bets carry ``market_odds``; allow both field names.
    combined_odds = math.prod(
        p.get("decimal_odds") if p.get("decimal_odds") is not None else p.get("market_odds", 1.0)
        for p in selected
    )
    combined_model_prob = math.prod(p.get("model_prob", 1.0) for p in selected)
    combined_edge = combined_model_prob - (1.0 / combined_odds) if combined_odds > 0 else 0.0

    risk_flag = combined_odds > 10 or legs_used >= 4

    return {
        "legs": selected,
        "legs_used": legs_used,
        "combined_odds": round(combined_odds, 4),
        "combined_model_prob": round(combined_model_prob, 4),
        "combined_edge": round(combined_edge, 4),
        "risk_flag": risk_flag,
        "independence_warning": (
            "Probabilities multiplied under independence assumption. "
            "Legs are from different matches."
        ),
    }
