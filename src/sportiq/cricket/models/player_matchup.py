"""Player matchup model — pure heuristic, no I/O."""

from __future__ import annotations

_BATTER_ROLES = {"batter", "wk-batter"}
_BOWLER_ROLES = {"bowler"}


def _role_kind(role: str | None) -> str:
    """Classify role as 'batter', 'bowler', or 'other'."""
    r = (role or "").lower().strip()
    if r in _BATTER_ROLES:
        return "batter"
    if r in _BOWLER_ROLES:
        return "bowler"
    return "other"


def compute_matchup(stats_a: dict, stats_b: dict) -> dict:
    """Compute a head-to-head matchup summary between two players.

    Args:
        stats_a: player_stats_chain payload for player_a.
        stats_b: player_stats_chain payload for player_b.

    Returns:
        Dict with player_a, player_b, role_a, role_b, matchup_type,
        edge_holder, edge_reason, and signals.
    """
    name_a = (stats_a or {}).get("name", "player_a")
    name_b = (stats_b or {}).get("name", "player_b")
    role_a_raw = (stats_a or {}).get("role")
    role_b_raw = (stats_b or {}).get("role")

    kind_a = _role_kind(role_a_raw)
    kind_b = _role_kind(role_b_raw)

    # Determine matchup type.
    batter_kinds = {"batter"}
    if kind_a in batter_kinds and kind_b in batter_kinds:
        matchup_type = "batter_vs_batter"
    elif kind_a == "bowler" and kind_b == "bowler":
        matchup_type = "bowler_vs_bowler"
    elif (kind_a in batter_kinds and kind_b == "bowler") or (kind_b in batter_kinds and kind_a == "bowler"):
        matchup_type = "batter_vs_bowler"
    else:
        matchup_type = "other"

    # Gather raw signals.
    batting_avg_a = (stats_a or {}).get("batting_avg")
    batting_avg_b = (stats_b or {}).get("batting_avg")
    bowling_avg_a = (stats_a or {}).get("bowling_avg")
    bowling_avg_b = (stats_b or {}).get("bowling_avg")
    sr_a = (stats_a or {}).get("strike_rate")
    sr_b = (stats_b or {}).get("strike_rate")

    signals = {
        "batting_avg_a": batting_avg_a,
        "batting_avg_b": batting_avg_b,
        "bowling_avg_a": bowling_avg_a,
        "bowling_avg_b": bowling_avg_b,
        "strike_rate_a": sr_a,
        "strike_rate_b": sr_b,
    }

    # Determine edge.
    edge_holder = "neutral"
    edge_reason = "Insufficient data to determine an edge."

    if matchup_type == "batter_vs_bowler":
        # Identify which player is the batter and which is the bowler.
        if kind_a in batter_kinds and kind_b == "bowler":
            batter_avg = batting_avg_a
            bowler_avg = bowling_avg_b
            batter_is_a = True
        else:
            batter_avg = batting_avg_b
            bowler_avg = bowling_avg_a
            batter_is_a = False

        if batter_avg is not None and bowler_avg is not None:
            if bowler_avg < batter_avg * 0.85:
                # Bowler condition is checked first (stricter).
                edge_holder = "player_b" if batter_is_a else "player_a"
                edge_reason = (
                    f"Bowler avg {bowler_avg:.1f} is <85% of batter avg {batter_avg:.1f} "
                    f"— bowler has the edge."
                )[:120]
            elif batter_avg > bowler_avg * 1.15:
                edge_holder = "player_a" if batter_is_a else "player_b"
                edge_reason = (
                    f"Batter avg {batter_avg:.1f} exceeds bowler avg {bowler_avg:.1f} "
                    f"by >15% — batter has the edge."
                )[:120]
            else:
                edge_holder = "neutral"
                edge_reason = "Stats too close to call a clear edge."

    elif matchup_type == "batter_vs_batter":
        if sr_a is not None and sr_b is not None and max(sr_a, sr_b) > 0:
            diff_frac = abs(sr_a - sr_b) / max(sr_a, sr_b)
            if diff_frac < 0.05:
                edge_holder = "neutral"
                edge_reason = "Strike rates within 5% — no clear edge."
            elif sr_a > sr_b:
                edge_holder = "player_a"
                edge_reason = f"player_a strike rate {sr_a:.1f} vs {sr_b:.1f} — higher SR wins."[:120]
            else:
                edge_holder = "player_b"
                edge_reason = f"player_b strike rate {sr_b:.1f} vs {sr_a:.1f} — higher SR wins."[:120]
        else:
            edge_holder = "neutral"
            edge_reason = "Strike rate data unavailable — neutral."

    elif matchup_type == "bowler_vs_bowler":
        edge_holder = "neutral"
        edge_reason = "Bowler vs bowler — no direct confrontation metric available."

    else:
        edge_holder = "neutral"
        edge_reason = "Role combination not directly comparable."

    return {
        "player_a": name_a,
        "player_b": name_b,
        "role_a": role_a_raw or "unknown",
        "role_b": role_b_raw or "unknown",
        "matchup_type": matchup_type,
        "edge_holder": edge_holder,
        "edge_reason": edge_reason,
        "signals": signals,
    }
