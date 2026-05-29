"""Tests for Elo helpers."""
from __future__ import annotations

from sportiq.football.models.elo import expected_score, update_rating


def test_equal_ratings_give_half():
    assert abs(expected_score(1800, 1800) - 0.5) < 1e-9


def test_higher_rating_favoured():
    assert expected_score(2000, 1600) > 0.5
    assert expected_score(1600, 2000) < 0.5


def test_expected_scores_complementary():
    a = expected_score(1900, 1700)
    b = expected_score(1700, 1900)
    assert abs(a + b - 1.0) < 1e-9


def test_home_advantage_raises_expectation():
    assert expected_score(1800, 1800, home_advantage=60) > 0.5


def test_win_raises_rating_loss_lowers():
    exp = expected_score(1800, 1800)
    won = update_rating(1800, exp, actual=1.0)
    lost = update_rating(1800, exp, actual=0.0)
    assert won > 1800 > lost


def test_draw_against_equal_is_neutral():
    exp = expected_score(1800, 1800)
    drew = update_rating(1800, exp, actual=0.5)
    assert abs(drew - 1800) < 1e-9
