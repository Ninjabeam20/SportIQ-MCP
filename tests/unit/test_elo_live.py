"""Unit tests for in-tournament Elo nudging — pure, no I/O."""
from __future__ import annotations

from sportiq.football.models.elo_live import nudge_ratings

_SEED = {"ARG": 2000.0, "BRA": 2000.0}


def test_toggle_off_returns_seed_unchanged():
    out = nudge_ratings(_SEED, [("ARG", "BRA", 3, 0)], enabled=False)
    assert out == _SEED
    assert out is not _SEED  # a copy, not the original


def test_winner_rating_rises_loser_falls():
    """A decisive result moves the winner up and the loser down by equal amounts."""
    out = nudge_ratings(_SEED, [("ARG", "BRA", 2, 0)], enabled=True)
    assert out["ARG"] > _SEED["ARG"]
    assert out["BRA"] < _SEED["BRA"]
    # Zero-sum at equal seeds (exp_a == 0.5): symmetric deltas.
    assert round(out["ARG"] - _SEED["ARG"], 6) == round(_SEED["BRA"] - out["BRA"], 6)


def test_draw_between_equals_is_noop():
    out = nudge_ratings(_SEED, [("ARG", "BRA", 1, 1)], enabled=True)
    assert out == _SEED


def test_unseeded_team_starts_at_default():
    out = nudge_ratings({"ARG": 2000.0}, [("ARG", "NZL", 1, 0)], enabled=True)
    assert out["NZL"] < 1500.0  # lost from the 1500 default
    assert out["ARG"] > 2000.0
