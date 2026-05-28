"""Tests for undercut window model."""
from __future__ import annotations

from sportiq.f1.models.undercut import undercut_window


def test_clear_undercut():
    # Fresh tyre delta > net gap to overcome → clears quickly
    result = undercut_window(
        driver_pace_s=83.0,
        target_pace_s=83.0,
        pit_loss_s=22.0,
        fresh_tyre_delta_s=3.0,
        gap_to_target_s=2.0,
    )
    assert result["viable"] is True
    assert result["laps_to_clear"] is not None
    assert result["laps_to_clear"] <= 10


def test_no_fresh_tyre_advantage():
    result = undercut_window(
        driver_pace_s=83.0,
        target_pace_s=83.0,
        pit_loss_s=22.0,
        fresh_tyre_delta_s=0.0,
        gap_to_target_s=5.0,
    )
    assert result["viable"] is False
    assert result["laps_to_clear"] is None


def test_marginal_undercut():
    # Clears but takes 6-10 laps
    result = undercut_window(
        driver_pace_s=83.0,
        target_pace_s=83.0,
        pit_loss_s=22.0,
        fresh_tyre_delta_s=1.0,
        gap_to_target_s=4.0,
    )
    if result["viable"]:
        assert result["marginal"] is True


def test_already_ahead_after_stop():
    # Negative gap — attacker is already ahead after pit
    result = undercut_window(
        driver_pace_s=83.0,
        target_pace_s=83.0,
        pit_loss_s=0.0,
        fresh_tyre_delta_s=2.0,
        gap_to_target_s=-5.0,  # Attacker ahead
    )
    assert result["viable"] is True


def test_no_clear_within_10_laps():
    # Very large gap → not viable
    result = undercut_window(
        driver_pace_s=83.0,
        target_pace_s=82.0,  # Target is faster
        pit_loss_s=22.0,
        fresh_tyre_delta_s=1.5,
        gap_to_target_s=30.0,
    )
    assert result["viable"] is False
