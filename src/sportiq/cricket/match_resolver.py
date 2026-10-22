"""Resolve a match_id to {team_a, team_b, venue, series_id}."""

from __future__ import annotations

from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.cricket.chains import fixtures_chain, scorecard_chain


def _match_teams_venue(m: dict) -> tuple[str, str, str]:
    """Teams + venue from a CricAPI match or a RapidAPI Cricbuzz ``matchInfo``."""
    teams = m.get("teams", [])
    team_a = teams[0] if len(teams) > 0 else m.get("team1", "")
    team_b = teams[1] if len(teams) > 1 else m.get("team2", "")
    # RapidAPI: team1/team2 are {"teamName", "teamSName"} objects.
    if isinstance(team_a, dict):
        team_a = team_a.get("teamName", "")
    if isinstance(team_b, dict):
        team_b = team_b.get("teamName", "")
    venue = m.get("venue") or (m.get("venueInfo") or {}).get("ground", "")
    return team_a, team_b, venue


def _series_id(m: dict) -> str | None:
    sid = m.get("series_id") or m.get("seriesId")
    return str(sid) if sid not in (None, "") else None


async def resolve_match(match_id: str) -> dict:
    """Return {team_a, team_b, venue, series_id} for a match_id.

    Tries fixtures_chain first (upcoming/live), falls back to scorecard_chain
    (live/completed). Accepts CricAPI (``id``/``teams``/``venue``/``series_id``)
    and RapidAPI Cricbuzz (``matchId``/``team1.teamName``/``venueInfo.ground``/
    ``seriesId``) shapes. ``series_id`` is None when the source omits it.
    Raises NotFoundError if neither yields usable data.
    """
    # Try fixtures first
    try:
        result = await fixtures_chain.fetch()
        matches = result.value.get("data") or result.value.get("matches") or []
        for m in matches:
            if str(m.get("id") or m.get("matchId") or "") == match_id:
                team_a, team_b, venue = _match_teams_venue(m)
                if team_a and team_b:
                    return {
                        "team_a": team_a,
                        "team_b": team_b,
                        "venue": venue,
                        "series_id": _series_id(m),
                    }
    except (AllSourcesFailedError, NotFoundError):
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
            return {
                "team_a": team_a,
                "team_b": team_b,
                "venue": venue,
                "series_id": _series_id(data),
            }
    except (AllSourcesFailedError, NotFoundError):
        pass

    raise NotFoundError(f"Could not resolve match_id={match_id!r} to team/venue info")
