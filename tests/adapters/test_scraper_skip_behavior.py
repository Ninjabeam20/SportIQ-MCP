"""S.8a — Assert NDTV and Cricbuzz scrapers raise MissingCredentialsError when disabled.

The no_live_credentials autouse fixture forces both toggles to False for every
test — these tests explicitly verify the skip behavior rather than relying on
implicit coverage. Per ADR-0007, scrapers are always off unless the operator
opts in via SPORTIQ_ENABLE_NDTV=1 / SPORTIQ_ENABLE_CRICBUZZ=1.
"""

import pytest

from sportiq.core.errors import MissingCredentialsError
from sportiq.cricket.adapters.cricbuzz_scraper import CricbuzzLiveMatchesAdapter
from sportiq.cricket.adapters.ndtv_sports_scraper import (
    NDTVLiveMatchesAdapter,
    NDTVScheduleAdapter,
)


async def test_ndtv_live_raises_when_disabled():
    """NDTV live adapter raises MissingCredentialsError when toggle is off."""
    adapter = NDTVLiveMatchesAdapter()
    with pytest.raises(MissingCredentialsError, match="SPORTIQ_ENABLE_NDTV"):
        await adapter.fetch()


async def test_ndtv_schedule_raises_when_disabled():
    """NDTV schedule adapter raises MissingCredentialsError when toggle is off."""
    adapter = NDTVScheduleAdapter()
    with pytest.raises(MissingCredentialsError, match="SPORTIQ_ENABLE_NDTV"):
        await adapter.fetch()


async def test_cricbuzz_live_raises_when_disabled():
    """Cricbuzz live adapter raises MissingCredentialsError when toggle is off."""
    adapter = CricbuzzLiveMatchesAdapter()
    with pytest.raises(MissingCredentialsError, match="SPORTIQ_ENABLE_CRICBUZZ"):
        await adapter.fetch()


async def test_ndtv_healthcheck_false_when_disabled():
    """NDTV healthcheck returns False when toggle is off."""
    adapter = NDTVLiveMatchesAdapter()
    assert await adapter.healthcheck() is False


async def test_cricbuzz_healthcheck_false_when_disabled():
    """Cricbuzz healthcheck returns False when toggle is off."""
    adapter = CricbuzzLiveMatchesAdapter()
    assert await adapter.healthcheck() is False
