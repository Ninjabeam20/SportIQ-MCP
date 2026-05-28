"""fastf1 local adapter — patches the fastf1 import to test lazy-import behavior."""
from __future__ import annotations

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
