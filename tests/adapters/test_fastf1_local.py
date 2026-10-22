"""fastf1 local adapter — patches the fastf1 import to test lazy-import behavior."""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import MagicMock, patch

import pytest


async def test_fastf1_laps_raises_when_not_installed():
    """When fastf1 is not importable, fetch() raises RuntimeError."""
    from sportiq.f1.adapters.fastf1_local import FastF1LapsAdapter

    with patch.dict(sys.modules, {"fastf1": None}):
        adapter = FastF1LapsAdapter()
        with pytest.raises(RuntimeError, match="fastf1 is not installed"):
            await adapter.fetch(session_key=9877, driver_number=1)


async def test_fastf1_standings_raises_when_not_installed():
    from sportiq.f1.adapters.fastf1_local import FastF1StandingsAdapter

    with patch.dict(sys.modules, {"fastf1": None}):
        adapter = FastF1StandingsAdapter()
        with pytest.raises(RuntimeError, match="fastf1 is not installed"):
            await adapter.fetch(year=2025)


async def test_fastf1_laps_raises_for_unknown_session_key():
    """When session_key is not in registry, raises RuntimeError."""
    from sportiq.f1.adapters.fastf1_local import FastF1LapsAdapter

    mock_fastf1 = MagicMock()
    with patch.dict(sys.modules, {"fastf1": mock_fastf1}):
        adapter = FastF1LapsAdapter()
        with pytest.raises(RuntimeError, match="not in static registry"):
            await adapter.fetch(session_key=99999, driver_number=1)


async def test_fastf1_healthcheck_true_when_installed():
    from sportiq.f1.adapters.fastf1_local import FastF1LapsAdapter

    mock_fastf1 = MagicMock()
    with patch.dict(sys.modules, {"fastf1": mock_fastf1}):
        adapter = FastF1LapsAdapter()
        assert await adapter.healthcheck() is True


async def test_fastf1_healthcheck_false_when_not_installed():
    from sportiq.f1.adapters.fastf1_local import FastF1LapsAdapter

    with patch.dict(sys.modules, {"fastf1": None}):
        adapter = FastF1LapsAdapter()
        assert await adapter.healthcheck() is False


async def test_fastf1_laps_offloads_to_thread(monkeypatch):
    from sportiq.f1.adapters.fastf1_local import FastF1LapsAdapter

    mock_fastf1 = MagicMock()
    mock_session = MagicMock()
    mock_laps = MagicMock()
    mock_laps.iterrows.return_value = [
        (
            0,
            {
                "LapNumber": 1,
                "LapTime": MagicMock(total_seconds=lambda: 82.5),
                "Compound": "SOFT",
                "TyreLife": 3,
            },
        )
    ]
    mock_session.laps.pick_drivers.return_value = mock_laps
    mock_fastf1.get_session.return_value = mock_session

    to_thread_called = False
    real_to_thread = asyncio.to_thread

    async def spy_to_thread(func, *args, **kwargs):
        nonlocal to_thread_called
        to_thread_called = True
        return await real_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", spy_to_thread)

    with patch.dict(sys.modules, {"fastf1": mock_fastf1}):
        adapter = FastF1LapsAdapter()
        result = await adapter.fetch(session_key=9877, driver_number=1)

    assert to_thread_called is True
    assert "laps" in result
    assert len(result["laps"]) == 1
    assert result["laps"][0]["lap_duration"] == 82.5
    assert result["laps"][0]["compound"] == "SOFT"


async def test_fastf1_standings_offloads_to_thread_and_bounds_rounds(monkeypatch):
    from sportiq.f1.adapters.fastf1_local import FastF1StandingsAdapter

    mock_fastf1 = MagicMock()
    mock_schedule = MagicMock()
    # round 0 (testing), round 1 (valid), round 99 (invalid out-of-bounds)
    mock_schedule.iterrows.return_value = [
        (0, {"RoundNumber": 0}),
        (1, {"RoundNumber": 1}),
        (2, {"RoundNumber": 99}),
    ]
    mock_fastf1.get_event_schedule.return_value = mock_schedule

    mock_session = MagicMock()
    mock_results = MagicMock()
    mock_results.iterrows.return_value = [
        (0, {"FullName": "Max Verstappen", "Position": 1, "Points": 25})
    ]
    mock_session.results = mock_results
    mock_fastf1.get_session.return_value = mock_session

    to_thread_called = False
    real_to_thread = asyncio.to_thread

    async def spy_to_thread(func, *args, **kwargs):
        nonlocal to_thread_called
        to_thread_called = True
        return await real_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", spy_to_thread)

    with patch.dict(sys.modules, {"fastf1": mock_fastf1}):
        adapter = FastF1StandingsAdapter()
        result = await adapter.fetch(year=2025)

    assert to_thread_called is True
    # Only round 1 was processed (round 0 skipped as testing, round 99 skipped as out of bounds)
    assert result["round"] == 1
    assert len(result["drivers"]) == 1
    assert result["drivers"][0]["name"] == "Max Verstappen"
    # Verify get_session was called only for round 1
    mock_fastf1.get_session.assert_called_once_with(2025, 1, "R")


async def test_fastf1_standings_sums_season_points_per_driver(monkeypatch):
    from sportiq.f1.adapters.fastf1_local import FastF1StandingsAdapter

    mock_fastf1 = MagicMock()
    schedule = MagicMock()
    schedule.iterrows.return_value = [(0, {"RoundNumber": 1}), (1, {"RoundNumber": 2})]
    mock_fastf1.get_event_schedule.return_value = schedule
    rows_by_round = {
        1: [
            {
                "FullName": "Lando Norris",
                "Abbreviation": "NOR",
                "DriverNumber": "1",
                "TeamName": "McLaren",
                "Position": 1,
                "Points": 25,
            },
            {
                "FullName": "Max Verstappen",
                "Abbreviation": "VER",
                "DriverNumber": "3",
                "TeamName": "Red Bull Racing",
                "Position": 2,
                "Points": 18,
            },
        ],
        2: [
            {
                "FullName": "Max Verstappen",
                "Abbreviation": "VER",
                "DriverNumber": "3",
                "TeamName": "Red Bull Racing",
                "Position": 1,
                "Points": 25,
            },
            {
                "FullName": "Lando Norris",
                "Abbreviation": "NOR",
                "DriverNumber": "1",
                "TeamName": "McLaren",
                "Position": 2,
                "Points": 18,
            },
        ],
    }

    def _session(year, round_num, kind):
        session = MagicMock()
        session.results.iterrows.return_value = list(enumerate(rows_by_round[round_num]))
        return session

    mock_fastf1.get_session.side_effect = _session
    with patch.dict(sys.modules, {"fastf1": mock_fastf1}):
        result = await FastF1StandingsAdapter().fetch(year=2026)

    assert result["season"] == 2026
    assert result["round"] == 2
    by_code = {d["code"]: d for d in result["drivers"]}
    assert by_code["NOR"]["points"] == 43.0
    assert by_code["VER"]["points"] == 43.0
    assert by_code["NOR"]["wins"] == 1
    assert by_code["NOR"]["driver_number"] == 1
    assert [d["position"] for d in result["drivers"]] == [1, 2]
    assert {t["team"]: t["points"] for t in result["constructors"]} == {
        "McLaren": 43.0,
        "Red Bull Racing": 43.0,
    }
