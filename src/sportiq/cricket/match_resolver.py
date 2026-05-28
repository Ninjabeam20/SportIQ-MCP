"""Resolve a CricAPI match_id to {team_a, team_b, venue}."""
from __future__ import annotations

from sportiq.core.errors import NotFoundError
from sportiq.cricket.chains import fixtures_chain, scorecard_chain


async def resolve_match(match_id: str) -> dict:
    """Return {team_a, team_b, venue} for a match_id.

    Tries fixtures_chain first (upcoming/live), falls back to scorecard_chain
    (live/completed). Raises NotFoundError if neither yields usable data.
    """
    # Try fixtures first
    try:
        result = await fixtures_chain.fetch()
        matches = result.value.get("data") or result.value.get("matches") or []
        for m in matches:
            if str(m.get("id", "")) == match_id:
                teams = m.get("teams", [])
                team_a = teams[0] if len(teams) > 0 else m.get("team1", "")
                team_b = teams[1] if len(teams) > 1 else m.get("team2", "")
                venue = m.get("venue", "")
                if team_a and team_b:
                    return {"team_a": team_a, "team_b": team_b, "venue": venue}
    except Exception:
        pass

    # Fall back to scorecard
    try:
        result = await scorecard_chain.fetch(match_id=match_id)
        data = result.value.get("data", result.value)
        team_info = data.get("teamInfo", [])
        team_a = team_info[0].get("name", "") if len(team_info) > 0 else data.get("team1", "")
        team_b = team_info[1].get("name", "") if len(team_info) > 1 else data.get("team2", "")
        venue = data.get("venue", "")
        if team_a and team_b:
            return {"team_a": team_a, "team_b": team_b, "venue": venue}
    except Exception:
        pass

    raise NotFoundError(f"Could not resolve match_id={match_id!r} to team/venue info")
