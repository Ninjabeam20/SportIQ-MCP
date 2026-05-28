"""Tyre data ordering invariants and points table correctness."""
from __future__ import annotations

from sportiq.f1.data.points import (
    RACE_POINTS,
    SPRINT_POINTS,
    race_points_for_position,
    sprint_points_for_position,
)
from sportiq.f1.data.tyres import TYRE_SPECS, TyreCompound


def test_soft_faster_than_medium_than_hard():
    soft = TYRE_SPECS[TyreCompound.SOFT]
    medium = TYRE_SPECS[TyreCompound.MEDIUM]
    hard = TYRE_SPECS[TyreCompound.HARD]
    # Negative delta = faster. SOFT < MEDIUM < HARD
    assert soft.base_lap_delta_s < medium.base_lap_delta_s < hard.base_lap_delta_s


def test_soft_degrades_faster_than_medium_than_hard():
    soft = TYRE_SPECS[TyreCompound.SOFT]
    medium = TYRE_SPECS[TyreCompound.MEDIUM]
    hard = TYRE_SPECS[TyreCompound.HARD]
    assert soft.degradation_rate_s_per_lap > medium.degradation_rate_s_per_lap > hard.degradation_rate_s_per_lap


def test_soft_shorter_window_than_hard():
    soft = TYRE_SPECS[TyreCompound.SOFT]
    hard = TYRE_SPECS[TyreCompound.HARD]
    assert soft.safe_window_laps < hard.safe_window_laps


def test_all_compounds_present():
    assert set(TYRE_SPECS.keys()) == set(TyreCompound)


def test_race_points_table_fia():
    assert RACE_POINTS[0] == 25   # P1
    assert RACE_POINTS[1] == 18   # P2
    assert RACE_POINTS[2] == 15   # P3
    assert RACE_POINTS[9] == 1    # P10
    assert len(RACE_POINTS) == 10


def test_sprint_points_table_fia():
    assert SPRINT_POINTS[0] == 8
    assert SPRINT_POINTS[-1] == 1
    assert len(SPRINT_POINTS) == 8


def test_race_points_for_position_p1():
    assert race_points_for_position(1) == 25


def test_race_points_fastest_lap_bonus():
    assert race_points_for_position(1, fastest_lap=True) == 26
    assert race_points_for_position(10, fastest_lap=True) == 2
    # Outside top 10: no bonus
    assert race_points_for_position(11, fastest_lap=True) == 0


def test_sprint_points_for_position():
    assert sprint_points_for_position(1) == 8
    assert sprint_points_for_position(8) == 1
    assert sprint_points_for_position(9) == 0
