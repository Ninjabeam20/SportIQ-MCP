"""Shared payload normalisers for cricket adapters.

The dream11 solver and other downstream models expect a uniform squad shape
regardless of which source served the data. Each adapter calls a helper here
before returning, so the chain output stays consistent.
"""

from __future__ import annotations

# Canonical roles. The solver groups players by these four codes.
_CANONICAL_ROLES = {"BAT", "BOWL", "ALL", "WK-BAT"}

_ROLE_ALIASES = {
    "BATSMAN": "BAT",
    "BATTER": "BAT",
    "BAT": "BAT",
    "BOWLER": "BOWL",
    "BOWL": "BOWL",
    "ALL-ROUNDER": "ALL",
    "ALLROUNDER": "ALL",
    "ALL": "ALL",
    "WK": "WK-BAT",
    "WK-BAT": "WK-BAT",
    "WICKET-KEEPER": "WK-BAT",
    "WICKETKEEPER": "WK-BAT",
    "KEEPER": "WK-BAT",
}


def canonical_role(role: str | None) -> str:
    """Map an upstream role string to one of {BAT, BOWL, ALL, WK-BAT}."""
    if not role:
        return "BAT"
    key = role.strip().upper().replace("_", "-")
    return _ROLE_ALIASES.get(key, "BAT")


def normalise_squad_payload(
    payload: dict,
    *,
    source: str,
    team: str | None = None,
) -> dict:
    """Coerce a per-source squad payload into the uniform shape.

    Output:
        {
            "players": [{"name", "role", "credits", "team"}, ...],
            "team": <team or None>,
            "source": <source name>,
        }

    For source="cricapi" the live ``/series_squad`` shape is
    ``{"data": [{"teamName": ..., "players": [...]}]}`` — ``data`` is a LIST of
    squad blocks. (Older/doc samples nest it as ``{"data": {"squad": [...]}}``;
    we accept both.) Each block names its team via ``teamName`` (live) or
    ``team`` (legacy). If a ``team`` filter is given we keep only the matching
    block; otherwise we flatten every player from every team.

    For source="static_seed" the input is already keyed by team — we just
    inject ``team`` into each player record.
    """
    players: list[dict] = []
    resolved_team = team

    if source == "cricapi":
        data = (payload or {}).get("data", [])
        # Live API: data is a list of squad blocks. Legacy/doc shape nests them
        # under data["squad"]. Anything else → no squads.
        if isinstance(data, list):
            squads = data
        elif isinstance(data, dict):
            squads = data.get("squad", [])
        else:
            squads = []
        wanted = (team or "").strip().upper()
        for block in squads:
            block_team = block.get("teamName") or block.get("team", "")
            if wanted and wanted not in block_team.upper():
                continue
            for p in block.get("players", []):
                players.append(
                    {
                        "name": p.get("name", ""),
                        "role": canonical_role(p.get("role")),
                        "credits": float(p.get("credits", 0.0)),
                        "team": block_team,
                    }
                )
        if not resolved_team and squads:
            resolved_team = squads[0].get("teamName") or squads[0].get("team")
    elif source == "static_seed":
        raw_players = (payload or {}).get("players", [])
        for p in raw_players:
            players.append(
                {
                    "name": p.get("name", ""),
                    "role": canonical_role(p.get("role")),
                    "credits": float(p.get("credits", 0.0)),
                    "team": team or "",
                }
            )
    else:
        # Unknown source — return empty rather than guess at the shape.
        pass

    return {"players": players, "team": resolved_team, "source": source}
