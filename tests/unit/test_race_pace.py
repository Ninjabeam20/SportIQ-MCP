"""Unit tests for the compare_race_pace pure function."""
from sportiq.f1.models.race_pace import compare_race_pace


def _make_laps(compound: str, count: int = 5, base_time: float = 80.0, driver_offset: float = 0.0) -> list[dict]:
    """Create minimal lap dicts with compound + tyre_life already set."""
    return [
        {
            "lap_number": i,
            "compound": compound,
            "tyre_life": i,
            "lap_duration": base_time + driver_offset + i * 0.1,
        }
        for i in range(1, count + 1)
    ]


async def test_compare_basic():
    laps_a = _make_laps("MEDIUM")
    laps_b = _make_laps("MEDIUM", base_time=81.0)
    result = compare_race_pace(laps_a, [], laps_b, [], driver_a=1, driver_b=33)
    assert result["compounds_compared"] == 1
    assert len(result["by_compound"]) == 1
    entry = result["by_compound"][0]
    assert entry["compound"] == "MEDIUM"
    assert entry["sample_count_a"] == 5
    assert entry["sample_count_b"] == 5


async def test_no_shared_compound():
    laps_a = _make_laps("SOFT")
    laps_b = _make_laps("MEDIUM")
    result = compare_race_pace(laps_a, [], laps_b, [], driver_a=1, driver_b=44)
    assert result["compounds_compared"] == 0
    assert result["by_compound"] == []


async def test_faster_driver_identified():
    # driver_a on MEDIUM: base 80.0 → lower intercept (faster)
    # driver_b on MEDIUM: base 82.0 → higher intercept (slower)
    laps_a = _make_laps("MEDIUM", base_time=80.0)
    laps_b = _make_laps("MEDIUM", base_time=82.0)
    result = compare_race_pace(laps_a, [], laps_b, [], driver_a=1, driver_b=44)
    assert result["compounds_compared"] == 1
    entry = result["by_compound"][0]
    # intercept_a < intercept_b → pace_delta_s negative
    assert entry["pace_delta_s"] < 0
    assert entry["faster_driver"] == 1


async def test_overall_faster_tie():
    # driver_a faster on SOFT, driver_b faster on HARD → tie
    laps_a_soft = _make_laps("SOFT", base_time=78.0)   # A faster on SOFT
    laps_b_soft = _make_laps("SOFT", base_time=80.0)
    laps_a_hard = _make_laps("HARD", base_time=84.0)   # B faster on HARD
    laps_b_hard = _make_laps("HARD", base_time=82.0)

    laps_a = laps_a_soft + laps_a_hard
    laps_b = laps_b_soft + laps_b_hard

    result = compare_race_pace(laps_a, [], laps_b, [], driver_a=1, driver_b=44)
    assert result["compounds_compared"] == 2
    assert result["overall_faster"] is None


async def test_empty_laps():
    result = compare_race_pace([], [], [], [], driver_a=1, driver_b=44)
    assert result["compounds_compared"] == 0
    assert result["by_compound"] == []
    assert result["overall_faster"] is None
