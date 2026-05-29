"""Value-bet math — implied prob, de-vig (sum-to-1), edge detection."""
from __future__ import annotations

import pytest

from sportiq.football.models.value_bet import devig, find_value, implied_prob


def test_implied_prob_is_reciprocal():
    assert implied_prob(2.0) == pytest.approx(0.5)
    assert implied_prob(4.0) == pytest.approx(0.25)


def test_implied_prob_rejects_nonpositive():
    with pytest.raises(ValueError):
        implied_prob(0)


def test_devig_normalises_to_one():
    # 2.0 / 4.0 / 4.0 imply 0.5 + 0.25 + 0.25 = 1.0 already (no vig) -> unchanged.
    out = devig({"home": 0.5, "draw": 0.25, "away": 0.25})
    assert sum(out.values()) == pytest.approx(1.0)
    assert out["home"] == pytest.approx(0.5)


def test_devig_removes_overround():
    # Implied sum to 1.05 (5% vig); devig scales each down proportionally.
    out = devig({"home": 0.55, "draw": 0.30, "away": 0.20})
    assert sum(out.values()) == pytest.approx(1.0)
    assert out["home"] == pytest.approx(0.55 / 1.05)


def test_devig_empty_input():
    assert devig({}) == {}


def test_find_value_flags_positive_edge():
    # Market home price 2.5 -> implied 0.4; with no other outcomes devig keeps... use full 1X2.
    # Bookmaker implies home 0.40/draw 0.286/away 0.40 (sum 1.086); devig home ~= 0.368.
    # Model gives home 0.50 -> edge ~0.13 >= 0.05 -> value on home.
    model = {"home_win": 0.50, "draw": 0.25, "away_win": 0.25}
    bookmaker = {"name": "TestBook", "home": 2.5, "draw": 3.5, "away": 2.5}
    picks = find_value(model, bookmaker, min_edge=0.05)
    assert any(p["outcome"] == "home" for p in picks)
    home = next(p for p in picks if p["outcome"] == "home")
    assert home["edge"] > 0
    assert home["market_odds"] == 2.5
    assert home["bookmaker"] == "TestBook"
    assert home["fair_odds"] == pytest.approx(2.0, abs=0.01)  # 1/0.50


def test_find_value_no_value_when_model_matches_market():
    # Fair book (no vig) matching the model exactly -> zero edge -> no picks at 0.05.
    model = {"home_win": 0.50, "draw": 0.25, "away_win": 0.25}
    bookmaker = {"name": "Fair", "home": 2.0, "draw": 4.0, "away": 4.0}
    assert find_value(model, bookmaker, min_edge=0.05) == []


def test_find_value_skips_missing_price():
    # Away price absent -> away outcome never considered; devig over the two present.
    model = {"home_win": 0.60, "draw": 0.20, "away_win": 0.20}
    bookmaker = {"name": "Partial", "home": 2.0, "draw": 3.0, "away": None}
    picks = find_value(model, bookmaker, min_edge=0.01)
    assert all(p["outcome"] != "away" for p in picks)
