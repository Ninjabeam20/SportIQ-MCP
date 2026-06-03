"""Unit tests for compute_form_trends — pure model, no I/O."""
from __future__ import annotations

from sportiq.football.models.form_trends import compute_form_trends


def _fx(home: str, away: str, hs: int, as_: int, date: str = "2026-01-01", **extra) -> dict:
    return {"home": home, "away": away, "home_goals": hs, "away_goals": as_, "date": date, **extra}


def _future(home: str, away: str, date: str = "2026-12-01") -> dict:
    return {"home": home, "away": away, "home_goals": None, "away_goals": None, "date": date}


# -- form_string ---------------------------------------------------------------


def test_form_string_correct():
    """5 completed matches produce correct W/D/L letters in chronological order."""
    fixtures = [
        _fx("Brazil", "Germany", 2, 1, "2026-01-01"),   # W (home)
        _fx("France", "Brazil", 1, 1, "2026-01-02"),    # D (away)
        _fx("Brazil", "Spain", 0, 2, "2026-01-03"),     # L (home)
        _fx("Argentina", "Brazil", 0, 3, "2026-01-04"), # W (away)
        _fx("Brazil", "Italy", 1, 1, "2026-01-05"),     # D (home)
    ]
    result = compute_form_trends(fixtures, "Brazil")
    assert result["form_string"] == "WDLWD"
    assert result["wins"] == 2
    assert result["draws"] == 2
    assert result["losses"] == 1
    assert result["matches_analysed"] == 5


# -- off-season / empty -------------------------------------------------------


def test_off_season_empty():
    """No completed fixtures → matches_analysed == 0 and form_string == ''."""
    fixtures = [_future("Brazil", "Germany"), _future("France", "Spain")]
    result = compute_form_trends(fixtures, "Brazil")
    assert result["matches_analysed"] == 0
    assert result["form_string"] == ""
    assert result["wins"] == result["draws"] == result["losses"] == 0
    assert result["goals_scored"] == 0
    assert result["goals_conceded"] == 0


# -- xG fields ----------------------------------------------------------------


def test_xg_populated_when_field_present():
    """Fixtures with xg_home/xg_away → non-None xg_for."""
    fixtures = [
        _fx("Brazil", "Germany", 2, 1, "2026-01-01", xg_home=1.8, xg_away=0.9),
        _fx("France", "Brazil", 0, 1, "2026-01-02", xg_home=0.7, xg_away=1.2),
    ]
    result = compute_form_trends(fixtures, "Brazil")
    assert result["xg_for"] is not None
    assert result["xg_against"] is not None
    # home match: xg_for=1.8; away match: xg_for=1.2 → total 3.0
    assert abs(result["xg_for"] - 3.0) < 0.01


def test_xg_none_when_field_absent():
    """Fixtures without xg_home/xg_away → xg_for is None."""
    fixtures = [_fx("Brazil", "Germany", 2, 1, "2026-01-01")]
    result = compute_form_trends(fixtures, "Brazil")
    assert result["xg_for"] is None
    assert result["xg_against"] is None


# -- recent_trend -------------------------------------------------------------


def test_recent_trend_improving():
    """Last 3 avg goals > prior 3 avg → 'improving'."""
    # prior 3: 0, 0, 0 goals; last 3: 3, 3, 3 goals
    fixtures = [
        _fx("Brazil", "A", 0, 1, "2026-01-01"),
        _fx("Brazil", "B", 0, 2, "2026-01-02"),
        _fx("Brazil", "C", 0, 0, "2026-01-03"),  # draw, 0 gf
        _fx("Brazil", "D", 3, 0, "2026-01-04"),
        _fx("Brazil", "E", 3, 1, "2026-01-05"),
        _fx("Brazil", "F", 3, 0, "2026-01-06"),
    ]
    result = compute_form_trends(fixtures, "Brazil")
    assert result["recent_trend"] == "improving"


def test_recent_trend_declining():
    """Last 3 avg goals < prior 3 avg → 'declining'."""
    # prior 3: 3, 3, 3 goals; last 3: 0, 0, 0 goals
    fixtures = [
        _fx("Brazil", "A", 3, 1, "2026-01-01"),
        _fx("Brazil", "B", 3, 0, "2026-01-02"),
        _fx("Brazil", "C", 3, 0, "2026-01-03"),
        _fx("Brazil", "D", 0, 2, "2026-01-04"),
        _fx("Brazil", "E", 0, 1, "2026-01-05"),
        _fx("Brazil", "F", 0, 3, "2026-01-06"),
    ]
    result = compute_form_trends(fixtures, "Brazil")
    assert result["recent_trend"] == "declining"


def test_recent_trend_stable_too_few():
    """Fewer than 4 completed matches → 'stable' regardless of goals."""
    fixtures = [
        _fx("Brazil", "A", 5, 0, "2026-01-01"),
        _fx("Brazil", "B", 0, 5, "2026-01-02"),
        _fx("Brazil", "C", 3, 0, "2026-01-03"),
    ]
    result = compute_form_trends(fixtures, "Brazil")
    assert result["recent_trend"] == "stable"


def test_case_insensitive_team_match():
    """Team matching is case-insensitive."""
    fixtures = [_fx("BRAZIL", "germany", 2, 0, "2026-01-01")]
    result = compute_form_trends(fixtures, "brazil")
    assert result["matches_analysed"] == 1
    assert result["wins"] == 1
