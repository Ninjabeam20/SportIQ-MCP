from sportiq.core.parlay import build_accumulator, normalise_pick


def test_normalise_pick_adds_sport_field():
    raw = {"event_id": "123", "outcome": "home", "edge": 0.10, "model_prob": 0.60, "market_odds": 2.0, "bookmaker": "bet365"}
    result = normalise_pick(raw, "football")
    assert result["sport"] == "football"
    assert result["match_id"] == "football:123"
    # Original fields still present
    assert result["outcome"] == "home"


def test_mixed_picks_no_cross_sport_dedup():
    """Same raw match_id in different sports should NOT dedup."""
    football_pick = normalise_pick(
        {"event_id": "123", "outcome": "home", "edge": 0.10, "model_prob": 0.60, "market_odds": 2.0, "bookmaker": "bet365"},
        "football",
    )
    cricket_pick = normalise_pick(
        {"event_id": "123", "outcome": "home", "edge": 0.09, "model_prob": 0.55, "market_odds": 2.2, "bookmaker": "betway"},
        "cricket",
    )
    result = build_accumulator([football_pick, cricket_pick], legs=3, min_edge=0.05)
    # Both should be included — different sport keys prevent dedup
    assert result["legs_used"] == 2


def test_both_sports_fail_zero_legs():
    """If both sports return no picks, legs_used == 0."""
    result = build_accumulator([], legs=3, min_edge=0.05)
    assert result["legs_used"] == 0


def test_one_sport_fails_gracefully():
    """If one sport has picks, acca is built from those picks only."""
    cricket_picks = [
        normalise_pick({"event_id": "c1", "outcome": "home", "edge": 0.10, "model_prob": 0.60, "market_odds": 2.0, "bookmaker": "b"}, "cricket"),
        normalise_pick({"event_id": "c2", "outcome": "away", "edge": 0.08, "model_prob": 0.50, "market_odds": 2.3, "bookmaker": "b"}, "cricket"),
    ]
    result = build_accumulator(cricket_picks, legs=3, min_edge=0.05)
    assert result["legs_used"] == 2
    assert all(leg["sport"] == "cricket" for leg in result["legs"])
