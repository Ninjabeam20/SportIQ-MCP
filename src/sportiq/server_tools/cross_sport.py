"""Cross-sport tools — combines football and cricket value picks."""
from __future__ import annotations

import asyncio

from sportiq.core.parlay import build_accumulator, normalise_pick
from sportiq.core.tool_response import Envelope, error_envelope
from sportiq.cricket.intel_tools import cricket_find_value_bets
from sportiq.football.intel_tools import football_find_value_bets


async def cross_sport_build_accumulator(legs: int = 3, min_edge: float = 0.05) -> Envelope:
    """Model the joint probability of multiple outcomes across football and cricket.

    Args:
        legs: Total legs across both sports (2-8). Default 3.
        min_edge: Minimum edge per leg. Default 0.05.

    Returns:
        data: same shape as football_build_accumulator, with sport field per leg.
        meta.estimated: true.
    """
    if not (2 <= legs <= 8):
        return error_envelope(code="INVALID_INPUT", message="legs must be between 2 and 8 inclusive.")
    if not (0.0 < min_edge < 1.0):
        return error_envelope(code="INVALID_INPUT", message="min_edge must be in (0, 1) exclusive.")

    football_r, cricket_r = await asyncio.gather(
        football_find_value_bets(min_edge=min_edge),
        cricket_find_value_bets(min_edge=min_edge),
        return_exceptions=True,
    )

    all_picks: list[dict] = []
    sports_available: list[str] = []
    notes: list[str] = []
    sub_metas: list[dict] = []

    # Collect football picks
    if not isinstance(football_r, Exception) and not football_r.get("error"):
        fb_picks = football_r.get("data", {}).get("value_bets", [])
        all_picks.extend(normalise_pick(p, "football") for p in fb_picks)
        sports_available.append("football")
        sub_metas.append(football_r.get("meta") or {})
    else:
        notes.append("football picks unavailable")

    # Collect cricket picks
    if not isinstance(cricket_r, Exception) and not cricket_r.get("error"):
        ck_picks = cricket_r.get("data", {}).get("value_bets", [])
        all_picks.extend(normalise_pick(p, "cricket") for p in ck_picks)
        sports_available.append("cricket")
        sub_metas.append(cricket_r.get("meta") or {})
    else:
        notes.append("cricket picks unavailable")

    if not sports_available:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="No value bets available from any sport.",
        )

    acca = build_accumulator(all_picks, legs=legs, min_edge=min_edge)

    # Aggregate freshness from the sub-tools — per fallback-contract.md the
    # worst-case staleness must be surfaced, never swallowed.
    meta: dict = {
        "source": "derived",
        "is_stale": any(m.get("is_stale", False) for m in sub_metas),
        "data_age_seconds": max((m.get("data_age_seconds", 0) for m in sub_metas), default=0),
        "fallback_used": any(m.get("fallback_used", False) for m in sub_metas),
        "duration_ms": sum(m.get("duration_ms", 0) for m in sub_metas),
        "estimated": True,
        "sports_available": sports_available,
    }
    if notes:
        meta["note"] = "; ".join(notes)

    return {"data": acca, "meta": meta}


def register_cross_sport_tools(mcp) -> None:
    """Register cross-sport tools on the supplied FastMCP instance."""
    from sportiq.core.tool_meta import READ_ONLY

    mcp.tool(annotations=READ_ONLY)(cross_sport_build_accumulator)
