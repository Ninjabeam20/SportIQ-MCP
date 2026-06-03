"""Unit tests for F1 qualifying analysis model."""
from sportiq.f1.models.quali_analysis import best_lap_per_driver, gap_to_pole, grid_projection


def test_best_lap_per_driver_picks_minimum():
    laps = [
        {"driver_number": 1, "lap_duration": 90.5},
        {"driver_number": 1, "lap_duration": 89.3},
        {"driver_number": 44, "lap_duration": 89.8},
    ]
    result = best_lap_per_driver(laps)
    assert result["1"] == 89.3
    assert result["44"] == 89.8


def test_best_lap_filters_invalid():
    laps = [
        {"driver_number": 1, "lap_duration": None},
        {"driver_number": 1, "lap_duration": -1},
        {"driver_number": 1, "lap_duration": 88.5},
        {"driver_number": 2, "lap_duration": "bad"},
    ]
    result = best_lap_per_driver(laps)
    assert result == {"1": 88.5}


def test_best_lap_empty():
    assert best_lap_per_driver([]) == {}


def test_gap_to_pole_pole_is_zero():
    bests = {"1": 89.3, "44": 89.8, "16": 90.1}
    gaps = gap_to_pole(bests)
    assert gaps["1"] == 0.0
    assert abs(gaps["44"] - 0.5) < 0.001
    assert next(iter(gaps.keys())) == "1"


def test_gap_to_pole_sorted_ascending():
    bests = {"44": 90.0, "1": 89.0, "16": 91.0}
    gaps = gap_to_pole(bests)
    values = list(gaps.values())
    assert values == sorted(values)


def test_gap_to_pole_empty():
    assert gap_to_pole({}) == {}


def test_grid_projection_structure():
    gaps = {"1": 0.0, "44": 0.5}
    info = {"1": {"full_name": "Max V", "team_name": "Red Bull"}}
    grid = grid_projection(gaps, info)
    assert grid[0]["position"] == 1
    assert grid[0]["driver_number"] == 1
    assert grid[0]["team_name"] == "Red Bull"
    assert grid[1]["position"] == 2
    assert grid[1]["full_name"] == "Driver #44"


def test_grid_projection_empty():
    assert grid_projection({}, {}) == []
