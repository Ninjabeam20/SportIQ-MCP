"""Pure-function form-trends model for football teams.

No I/O. Input is the ``fixtures`` list from ``football_fixtures_chain``.
"""
from __future__ import annotations


def compute_form_trends(fixtures: list[dict], team: str) -> dict:
    """Compute rolling form + xG trajectory for *team* from fixture history.

    Args:
        fixtures: List of fixture dicts from ``football_fixtures_chain``.
            Each dict has at minimum ``home_team``, ``away_team``,
            ``home_score``, ``away_score`` (``None`` for future), ``date``.
        team: Team name to analyse (case-insensitive match against
            ``home_team`` / ``away_team``).

    Returns:
        dict with keys: team, matches_analysed, form_string, wins, draws,
        losses, goals_scored, goals_conceded, xg_for, xg_against,
        recent_trend.
    """
    team_lower = team.strip().lower()

    # Filter to this team's completed fixtures (both scores present).
    completed: list[dict] = []
    for fx in fixtures:
        home = (fx.get("home_team") or "").lower()
        away = (fx.get("away_team") or "").lower()
        if team_lower not in (home, away):
            continue
        hs = fx.get("home_score")
        as_ = fx.get("away_score")
        if hs is None or as_ is None:
            continue
        completed.append(fx)

    # Sort ascending by date (ISO strings sort lexicographically).
    completed.sort(key=lambda fx: fx.get("date") or "")

    wins = draws = losses = 0
    goals_scored = goals_conceded = 0
    xg_for_total: float | None = None
    xg_against_total: float | None = None
    form_letters: list[str] = []
    goal_list: list[int] = []  # goals scored per match (for trend)

    for fx in completed:
        home = (fx.get("home_team") or "").lower()
        hs = int(fx["home_score"])
        as_ = int(fx["away_score"])

        is_home = team_lower == home
        gf = hs if is_home else as_
        ga = as_ if is_home else hs

        goals_scored += gf
        goals_conceded += ga
        goal_list.append(gf)

        if gf > ga:
            wins += 1
            form_letters.append("W")
        elif gf == ga:
            draws += 1
            form_letters.append("D")
        else:
            losses += 1
            form_letters.append("L")

        # xG — only if the fixture carries the field.
        xg_h = fx.get("xg_home")
        xg_a = fx.get("xg_away")
        if xg_h is not None and xg_a is not None:
            xg_for_raw = float(xg_h) if is_home else float(xg_a)
            xg_against_raw = float(xg_a) if is_home else float(xg_h)
            xg_for_total = (xg_for_total or 0.0) + xg_for_raw
            xg_against_total = (xg_against_total or 0.0) + xg_against_raw

    # recent_trend: compare avg goals in last 3 vs the 3 before that.
    if len(goal_list) >= 4:
        last3 = goal_list[-3:]
        prior3 = goal_list[-6:-3] if len(goal_list) >= 6 else goal_list[: len(goal_list) - 3]
        avg_last = sum(last3) / len(last3)
        avg_prior = sum(prior3) / len(prior3) if prior3 else avg_last
        if avg_last > avg_prior:
            recent_trend = "improving"
        elif avg_last < avg_prior:
            recent_trend = "declining"
        else:
            recent_trend = "stable"
    else:
        recent_trend = "stable"

    return {
        "team": team,
        "matches_analysed": len(completed),
        "form_string": "".join(form_letters),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_scored": goals_scored,
        "goals_conceded": goals_conceded,
        "xg_for": round(xg_for_total, 3) if xg_for_total is not None else None,
        "xg_against": round(xg_against_total, 3) if xg_against_total is not None else None,
        "recent_trend": recent_trend,
    }
