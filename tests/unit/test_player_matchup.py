"""Unit tests for the pure compute_matchup model."""

from sportiq.cricket.models.player_matchup import compute_matchup


def _batter(name="Player A", batting_avg=45.0, strike_rate=135.0):
    return {
        "name": name,
        "role": "batter",
        "batting_avg": batting_avg,
        "strike_rate": strike_rate,
        "bowling_avg": None,
        "economy_rate": None,
        "wickets": None,
    }


def _bowler(name="Player B", bowling_avg=28.0):
    return {
        "name": name,
        "role": "bowler",
        "batting_avg": None,
        "strike_rate": None,
        "bowling_avg": bowling_avg,
        "economy_rate": 7.5,
        "wickets": 50,
    }


# --- batter_vs_bowler edge cases ---

def test_batter_vs_bowler_batter_edge():
    """batter_avg(50) > bowler_avg(43) * 1.15(49.45), bowler NOT < 42.5 → player_a edge."""
    a = _batter("Virat", batting_avg=50.0)
    b = _bowler("Bumrah", bowling_avg=43.0)
    result = compute_matchup(a, b)
    assert result["matchup_type"] == "batter_vs_bowler"
    assert result["edge_holder"] == "player_a"


def test_batter_vs_bowler_bowler_edge():
    """bowling_avg(15) < batting_avg(20) * 0.85(17) → player_b (bowler) edge."""
    a = _batter("Batsman", batting_avg=20.0)
    b = _bowler("Bowler", bowling_avg=15.0)
    result = compute_matchup(a, b)
    assert result["matchup_type"] == "batter_vs_bowler"
    assert result["edge_holder"] == "player_b"


def test_batter_vs_bowler_neutral():
    """batting_avg=35, bowling_avg=32 — too close → neutral."""
    a = _batter("Batsman", batting_avg=35.0)
    b = _bowler("Bowler", bowling_avg=32.0)
    result = compute_matchup(a, b)
    assert result["matchup_type"] == "batter_vs_bowler"
    assert result["edge_holder"] == "neutral"


def test_batter_vs_bowler_reversed_order():
    """Bowler as player_a, batter as player_b — still correct."""
    a = _bowler("Bowler", bowling_avg=18.0)
    b = _batter("Batter", batting_avg=40.0)
    result = compute_matchup(a, b)
    assert result["matchup_type"] == "batter_vs_bowler"
    # bowling_avg(18) < batting_avg(40) * 0.85(34) → bowler edge → player_a
    assert result["edge_holder"] == "player_a"


# --- batter_vs_batter ---

def test_batter_vs_batter_higher_sr_wins():
    """player_a sr=145 >> player_b sr=110 → player_a edge."""
    a = _batter("A", strike_rate=145.0)
    b = _batter("B", strike_rate=110.0)
    result = compute_matchup(a, b)
    assert result["matchup_type"] == "batter_vs_batter"
    assert result["edge_holder"] == "player_a"


def test_batter_vs_batter_within_5_pct_neutral():
    """SR within 5% → neutral."""
    a = _batter("A", strike_rate=130.0)
    b = _batter("B", strike_rate=128.0)
    result = compute_matchup(a, b)
    assert result["matchup_type"] == "batter_vs_batter"
    assert result["edge_holder"] == "neutral"


# --- None stats → neutral, no crash ---

def test_none_stats_neutral():
    """All None stats → neutral, no crash."""
    a = {"name": "X", "role": "batter", "batting_avg": None, "strike_rate": None, "bowling_avg": None}
    b = {"name": "Y", "role": "bowler", "batting_avg": None, "strike_rate": None, "bowling_avg": None}
    result = compute_matchup(a, b)
    assert result["edge_holder"] == "neutral"
    assert "signals" in result


def test_empty_dicts_no_crash():
    """Completely empty dicts — should not crash."""
    result = compute_matchup({}, {})
    assert result["matchup_type"] == "other"
    assert result["edge_holder"] == "neutral"


# --- matchup type detection ---

def test_matchup_type_detection_wk_batter():
    """wk-batter role is treated as batter for matchup typing."""
    a = {"name": "WK", "role": "wk-batter", "batting_avg": 40.0, "strike_rate": 130.0, "bowling_avg": None}
    b = _bowler("Bowler", bowling_avg=22.0)
    result = compute_matchup(a, b)
    assert result["matchup_type"] == "batter_vs_bowler"


def test_matchup_type_detection_bowler_vs_bowler():
    a = _bowler("B1", bowling_avg=28.0)
    b = _bowler("B2", bowling_avg=30.0)
    result = compute_matchup(a, b)
    assert result["matchup_type"] == "bowler_vs_bowler"
    assert result["edge_holder"] == "neutral"


def test_matchup_type_detection_other():
    """all-rounder vs all-rounder → 'other'."""
    a = {"name": "AR1", "role": "all-rounder", "batting_avg": None, "strike_rate": None, "bowling_avg": None}
    b = {"name": "AR2", "role": "all-rounder", "batting_avg": None, "strike_rate": None, "bowling_avg": None}
    result = compute_matchup(a, b)
    assert result["matchup_type"] == "other"
    assert result["edge_holder"] == "neutral"


def test_signals_always_present():
    """signals dict is always returned with the expected keys."""
    result = compute_matchup(_batter(), _bowler())
    for key in ["batting_avg_a", "batting_avg_b", "bowling_avg_a", "bowling_avg_b", "strike_rate_a", "strike_rate_b"]:
        assert key in result["signals"], f"missing signal key: {key}"


def test_edge_reason_max_120_chars():
    """edge_reason must not exceed 120 characters."""
    result = compute_matchup(_batter("A", batting_avg=99.0), _bowler("B", bowling_avg=10.0))
    assert len(result["edge_reason"]) <= 120


# --- Cassette-shape tests (unwrapped CricAPI and RapidAPI) ---

def test_unwrapped_cricapi_cassette_shape_non_other():
    """Feed unwrapped CricAPI cassette shape → non-other matchup with signals."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parents[1] / "fixtures" / "cricapi" / "players_info.json"
    raw_fixture = json.loads(fixture_path.read_text())
    # CricAPI adapter unwraps response.data:
    kohli_unwrapped = raw_fixture["data"]

    bumrah_unwrapped = {
        "id": "p_bumrah_001",
        "name": "Jasprit Bumrah",
        "playingRole": "Bowler",
        "stats": [
            {"fn": "bowling", "matchtype": "t20i", "stat": "Average", "value": "19.66"},
            {"fn": "bowling", "matchtype": "t20i", "stat": "Economy", "value": "6.55"},
            {"fn": "bowling", "matchtype": "t20i", "stat": "Wickets", "value": "74"},
        ],
    }

    result = compute_matchup(kohli_unwrapped, bumrah_unwrapped)
    assert result["matchup_type"] == "batter_vs_bowler"
    assert result["edge_holder"] == "player_b"
    assert result["player_a"] == "Virat Kohli"
    assert result["player_b"] == "Jasprit Bumrah"
    assert result["role_a"] == "Batter"
    assert result["role_b"] == "Bowler"
    assert result["signals"]["batting_avg_a"] == 51.39
    assert result["signals"]["strike_rate_a"] == 137.96
    assert result["signals"]["bowling_avg_b"] == 19.66


def test_wrapped_cricapi_shape_non_other():
    """Feed wrapped {data: {stats}} CricAPI shape → non-other matchup."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parents[1] / "fixtures" / "cricapi" / "players_info.json"
    kohli_wrapped = json.loads(fixture_path.read_text())

    bumrah_wrapped = {
        "data": {
            "name": "Jasprit Bumrah",
            "playingRole": "Bowler",
            "stats": [
                {"fn": "bowling", "matchtype": "t20i", "stat": "Average", "value": "19.66"},
            ],
        }
    }

    result = compute_matchup(kohli_wrapped, bumrah_wrapped)
    assert result["matchup_type"] == "batter_vs_bowler"
    assert result["edge_holder"] == "player_b"
    assert result["signals"]["batting_avg_a"] == 51.39
    assert result["signals"]["bowling_avg_b"] == 19.66


def test_rapidapi_career_shape_in_matchup():
    """Feed RapidAPI values shape with role → non-other matchup."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parents[1] / "fixtures" / "rapidapi" / "player_career.json"
    rapid_data = json.loads(fixture_path.read_text())
    rapid_batter = {"role": "batter", **rapid_data}

    bowler = _bowler("Bumrah", bowling_avg=20.0)

    result = compute_matchup(rapid_batter, bowler)
    assert result["matchup_type"] == "batter_vs_bowler"
    assert result["signals"]["batting_avg_a"] == 51.39
    assert result["signals"]["strike_rate_a"] == 137.96
