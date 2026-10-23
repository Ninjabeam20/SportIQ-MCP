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


def _team_name(t: object) -> str:
    if isinstance(t, dict):
        return str(t.get("name") or t.get("teamName") or "")
    return str(t or "")


def _scorecard_teams_venue(data: dict) -> tuple[str, str, str, str | None]:
    """Teams, venue and series id from any recorded scorecard shape.

    CricAPI ``match_scorecard`` (unwrapped): ``teams`` (names) / ``teamInfo``.
    RapidAPI Cricbuzz ``scard``: ``matchHeader.team1/team2`` as ``{name, shortName}``.
    Legacy/synthetic: top-level ``team1``/``team2``.
    """
    header = data.get("matchHeader") or {}
    team_info = data.get("teamInfo") or []
    teams = data.get("teams") or []
    if len(team_info) > 1:
        team_a, team_b = _team_name(team_info[0]), _team_name(team_info[1])
    elif len(teams) > 1:
        team_a, team_b = _team_name(teams[0]), _team_name(teams[1])
    elif header.get("team1") and header.get("team2"):
        team_a, team_b = _team_name(header["team1"]), _team_name(header["team2"])
    else:
        team_a, team_b = _team_name(data.get("team1")), _team_name(data.get("team2"))
    venue = (
        data.get("venue")
        or header.get("venue")
        or (data.get("venueInfo") or header.get("venueInfo") or {}).get("ground", "")
    )
    return team_a, team_b, venue or "", _series_id(data) or _series_id(header)


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
        team_a, team_b, venue, series_id = _scorecard_teams_venue(data)
        if team_a and team_b:
            return {
                "team_a": team_a,
                "team_b": team_b,
                "venue": venue,
                "series_id": series_id,
            }
    except (AllSourcesFailedError, NotFoundError):
        pass

    raise NotFoundError(f"Could not resolve match_id={match_id!r} to team/venue info")
