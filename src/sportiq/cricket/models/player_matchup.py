"""Player matchup model — pure heuristic, no I/O."""

from __future__ import annotations

import contextlib

_BATTER_ROLES = {"batter", "wk-batter", "bat", "wk-bat", "wicketkeeper batter"}
_BOWLER_ROLES = {"bowler", "bowl"}


def _role_kind(role: str | None) -> str:
    """Classify role as 'batter', 'bowler', or 'other'."""
    r = (role or "").lower().strip()
    if r in _BATTER_ROLES:
        return "batter"
    if r in _BOWLER_ROLES:
        return "bowler"
    return "other"


def extract_player_stats(payload: dict | None) -> dict:
    """Extract player profile and T20 career statistics from various payload shapes.

    Accepts:
      - Wrapped CricAPI: ``{"data": {"name": ..., "playingRole": ..., "stats": [...]}}``
      - Unwrapped CricAPI: ``{"name": ..., "playingRole": ..., "stats": [...]}``
      - RapidAPI Cricbuzz: ``{"values": [{"name": "T20I", ...}], "appIndex": ...}``
      - Flat / synthetic dicts: ``{"name": ..., "role": ..., "batting_avg": ..., ...}``
    """
    if not payload or not isinstance(payload, dict):
        return {
            "name": None,
            "role": None,
            "batting_avg": None,
            "strike_rate": None,
            "bowling_avg": None,
            "economy_rate": None,
            "wickets": None,
        }

    inner = payload.get("data")
    data = inner if isinstance(inner, dict) else payload

    name = data.get("name") or payload.get("name")
    if not name:
        app_idx = data.get("appIndex") or payload.get("appIndex")
        if isinstance(app_idx, dict) and app_idx.get("seoTitle"):
            name = app_idx["seoTitle"].removesuffix(" Career").strip()

    role = (
        data.get("role")
        or data.get("playingRole")
        or payload.get("role")
        or payload.get("playingRole")
    )

    batting_avg = data.get("batting_avg") if data.get("batting_avg") is not None else payload.get("batting_avg")
    strike_rate = data.get("strike_rate") if data.get("strike_rate") is not None else payload.get("strike_rate")
    bowling_avg = data.get("bowling_avg") if data.get("bowling_avg") is not None else payload.get("bowling_avg")
    economy_rate = data.get("economy_rate") if data.get("economy_rate") is not None else payload.get("economy_rate")
    wickets = data.get("wickets") if data.get("wickets") is not None else payload.get("wickets")

    if batting_avg is not None:
        try:
            batting_avg = float(batting_avg)
        except (TypeError, ValueError):
            batting_avg = None
    if strike_rate is not None:
        try:
            strike_rate = float(strike_rate)
        except (TypeError, ValueError):
            strike_rate = None
    if bowling_avg is not None:
        try:
            bowling_avg = float(bowling_avg)
        except (TypeError, ValueError):
            bowling_avg = None
    if economy_rate is not None:
        try:
            economy_rate = float(economy_rate)
        except (TypeError, ValueError):
            economy_rate = None
    if wickets is not None:
        try:
            wickets = int(float(wickets))
        except (TypeError, ValueError):
            wickets = None

    # 1. CricAPI stats shape: list of {"fn", "matchtype", "stat", "value"}
    cric_rows = data.get("stats") or payload.get("stats")
    if isinstance(cric_rows, list) and cric_rows:
        target_rows = [
            r for r in cric_rows
            if isinstance(r, dict) and str(r.get("matchtype", "")).lower().strip() == "t20i"
        ]
        if not target_rows:
            target_rows = [
                r for r in cric_rows
                if isinstance(r, dict) and str(r.get("matchtype", "")).lower().strip() in ("t20", "ipl")
            ]

        for row in target_rows:
            fn = str(row.get("fn", "")).lower().strip()
            stat = str(row.get("stat", "")).lower().strip()
            val = row.get("value")
            if val is None or val == "-" or val == "":
                continue
            try:
                num = float(val)
            except (TypeError, ValueError):
                continue

            if fn == "batting":
                if stat in ("average", "avg") and batting_avg is None:
                    batting_avg = num
                elif stat in ("strike rate", "strikerate", "sr") and strike_rate is None:
                    strike_rate = num
            elif fn == "bowling":
                if stat in ("average", "avg") and bowling_avg is None:
                    bowling_avg = num
                elif stat in ("economy", "economy rate", "econ") and economy_rate is None:
                    economy_rate = num
                elif stat in ("wickets", "wkts", "w") and wickets is None:
                    wickets = int(num)
            else:
                if stat in ("average", "avg") and batting_avg is None:
                    batting_avg = num
                elif stat in ("strike rate", "strikerate", "sr") and strike_rate is None:
                    strike_rate = num
                elif stat in ("economy", "economy rate", "econ") and economy_rate is None:
                    economy_rate = num
                elif stat in ("wickets", "wkts") and wickets is None:
                    wickets = int(num)

    # 2. RapidAPI Cricbuzz shape: list of values e.g. [{"name": "T20I", ...}]
    rapid_rows = data.get("values") or payload.get("values")
    if isinstance(rapid_rows, list) and rapid_rows:
        target_rows = [
            r for r in rapid_rows
            if isinstance(r, dict) and str(r.get("name", "")).upper().strip() == "T20I"
        ]
        if not target_rows:
            target_rows = [
                r for r in rapid_rows
                if isinstance(r, dict) and str(r.get("name", "")).upper().strip() in ("T20", "IPL")
            ]

        for row in target_rows:
            if batting_avg is None:
                b_avg = row.get("average") or row.get("battingAverage")
                if b_avg is not None and b_avg != "-" and b_avg != "":
                    with contextlib.suppress(TypeError, ValueError):
                        batting_avg = float(b_avg)
            if strike_rate is None:
                sr = row.get("strikeRate") or row.get("strike_rate")
                if sr is not None and sr != "-" and sr != "":
                    with contextlib.suppress(TypeError, ValueError):
                        strike_rate = float(sr)
            if bowling_avg is None:
                bw_avg = row.get("bowlingAverage")
                if bw_avg is not None and bw_avg != "-" and bw_avg != "":
                    with contextlib.suppress(TypeError, ValueError):
                        bowling_avg = float(bw_avg)
            if economy_rate is None:
                econ = row.get("economy") or row.get("economyRate")
                if econ is not None and econ != "-" and econ != "":
                    with contextlib.suppress(TypeError, ValueError):
                        economy_rate = float(econ)
            if wickets is None:
                w = row.get("wickets")
                if w is not None and w != "-" and w != "":
                    with contextlib.suppress(TypeError, ValueError):
                        wickets = int(float(w))

    return {
        "name": name,
        "role": role,
        "batting_avg": batting_avg,
        "strike_rate": strike_rate,
        "bowling_avg": bowling_avg,
        "economy_rate": economy_rate,
        "wickets": wickets,
    }


def compute_matchup(stats_a: dict, stats_b: dict) -> dict:
    """Compute a head-to-head matchup summary between two players.

    Args:
        stats_a: player_stats_chain payload for player_a.
        stats_b: player_stats_chain payload for player_b.

    Returns:
        Dict with player_a, player_b, role_a, role_b, matchup_type,
        edge_holder, edge_reason, and signals.
    """
    p_a = extract_player_stats(stats_a)
    p_b = extract_player_stats(stats_b)

    name_a = p_a.get("name") or (stats_a or {}).get("name", "player_a")
    name_b = p_b.get("name") or (stats_b or {}).get("name", "player_b")
    role_a_raw = p_a.get("role")
    role_b_raw = p_b.get("role")

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
    batting_avg_a = p_a.get("batting_avg")
    batting_avg_b = p_b.get("batting_avg")
    bowling_avg_a = p_a.get("bowling_avg")
    bowling_avg_b = p_b.get("bowling_avg")
    sr_a = p_a.get("strike_rate")
    sr_b = p_b.get("strike_rate")

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
