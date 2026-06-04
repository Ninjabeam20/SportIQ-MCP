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
