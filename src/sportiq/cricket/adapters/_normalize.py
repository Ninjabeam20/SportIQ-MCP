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


def _player_id(p: dict) -> str | None:
    """Provider player ID (CricAPI/RapidAPI ``id``, seed ``player_id``), stringified."""
    pid = p.get("id") or p.get("player_id")
    return str(pid) if pid not in (None, "") else None


def _credits(p: dict) -> float | None:
    """Contest credits, or None when the source has none (never a fake 0.0)."""
    raw = p.get("credits")
    return float(raw) if raw not in (None, "") else None


def normalise_squad_payload(
    payload: dict,
    *,
    source: str,
    team: str | None = None,
) -> dict:
    """Coerce a per-source squad payload into the uniform shape.

    Output:
        {
            "players": [{"name", "role", "credits", "team", "player_id"}, ...],
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

    ``player_id`` is the provider ID (stringified) or None; ``credits`` is None
    when the source carries no credits.
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
        from sportiq.cricket.teams import IPL_TEAM_NAMES, resolve_team_code

        wanted = (team or "").strip().upper()
        # Resolve the filter to a code ("Mumbai Indians" → "MI"). Exact matches
        # only: a substring test matched nothing for "MI" and both PBKS and CSK
        # for "Kings".
        wanted_code = resolve_team_code(wanted, IPL_TEAM_NAMES) or wanted
        for block in squads:
            block_team = block.get("teamName") or block.get("team") or ""
            if wanted and not (
                resolve_team_code(block_team, IPL_TEAM_NAMES) == wanted_code
                or block_team.upper() == wanted
            ):
                continue
            for p in block.get("players", []):
                players.append(
                    {
                        "name": p.get("name", ""),
                        "role": canonical_role(p.get("role")),
                        "credits": _credits(p),
                        "team": block_team,
                        "player_id": _player_id(p),
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
                    "credits": _credits(p),
                    "team": team or "",
                    "player_id": _player_id(p),
                }
            )
    else:
        # Unknown source — return empty rather than guess at the shape.
        pass

    return {"players": players, "team": resolved_team, "source": source}
