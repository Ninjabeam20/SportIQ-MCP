"""form_index — synthetic inputs cover rising / stable / falling / no-data."""

from __future__ import annotations

from sportiq.cricket.models.form_index import compute_form_index, player_form_index


def test_form_score_is_bounded_0_to_100():
    # Wildly explosive synthetic — should saturate at 100.
    innings = [{"runs": 200, "balls": 60}] * 5
    result = compute_form_index(innings, career_avg=70.0, career_sr=180.0)
    assert 0.0 <= result["form_score"] <= 100.0
    assert result["form_score"] == 100.0


def test_empty_recent_falls_back_to_career_baseline():
    result = compute_form_index([], career_avg=40.0, career_sr=130.0)
    # career baseline = avg(40) + (130-100)*0.4 (=12) = 52
    assert result["samples"] == 0
    assert result["trend"] == "stable"
    assert 50.0 <= result["form_score"] <= 55.0


def test_rising_trend_when_latest_is_explosive():
    innings = [
        {"runs": 80, "balls": 40},   # latest
        {"runs": 10, "balls": 12},
        {"runs": 5, "balls": 8},
        {"runs": 12, "balls": 14},
        {"runs": 20, "balls": 18},
    ]
    result = compute_form_index(innings, career_avg=35.0, career_sr=140.0)
    assert result["trend"] == "rising"


def test_falling_trend_when_latest_is_collapse():
    innings = [
        {"runs": 2, "balls": 5},     # latest — duck-ish
        {"runs": 60, "balls": 38},
        {"runs": 45, "balls": 28},
        {"runs": 72, "balls": 50},
        {"runs": 38, "balls": 30},
    ]
    result = compute_form_index(innings, career_avg=45.0, career_sr=140.0)
    assert result["trend"] == "falling"


def test_bowler_wickets_credit_pulls_score_up():
    bat_only = [{"runs": 5, "balls": 4} for _ in range(5)]
    with_wickets = [{"runs": 5, "balls": 4, "wickets": 3} for _ in range(5)]
    a = compute_form_index(bat_only, career_avg=10.0, career_sr=110.0)
    b = compute_form_index(with_wickets, career_avg=10.0, career_sr=110.0)
    assert b["form_score"] > a["form_score"]


def test_samples_reflects_only_recent_window():
    innings = [{"runs": 30, "balls": 25}] * 12
    result = compute_form_index(innings, career_avg=30.0, career_sr=130.0)
    assert result["samples"] == 5  # weighted window is 5 newest


# --- Cassette-shape tests (unwrapped CricAPI and RapidAPI) ---

def test_player_form_index_unwrapped_cricapi():
    """Unwrapped CricAPI cassette payload derives non-50 form score from career stats."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parents[1] / "fixtures" / "cricapi" / "players_info.json"
    raw_fixture = json.loads(fixture_path.read_text())
    unwrapped = raw_fixture["data"]

    result = player_form_index(unwrapped)
    # Kohli career avg 51.39, sr 137.96 -> baseline ~66.6
    assert result["form_score"] > 55.0
    assert result["trend"] == "stable"
    assert result["samples"] == 0


def test_player_form_index_wrapped_cricapi():
    """Wrapped {data: {stats}} CricAPI payload also derives form score."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parents[1] / "fixtures" / "cricapi" / "players_info.json"
    wrapped = json.loads(fixture_path.read_text())

    result = player_form_index(wrapped)
    assert result["form_score"] > 55.0


def test_player_form_index_rapidapi_career():
    """RapidAPI career values shape derives form score."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parents[1] / "fixtures" / "rapidapi" / "player_career.json"
    rapid_data = json.loads(fixture_path.read_text())

    result = player_form_index(rapid_data)
    # T20I avg 51.39, sr 137.96 -> baseline ~66.6
    assert result["form_score"] > 55.0
