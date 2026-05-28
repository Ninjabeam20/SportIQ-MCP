"""FallbackChain behavior for F1 chains — all adapters stubbed."""

from __future__ import annotations

import pytest

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.fallback import FallbackChain


class _OK:
    def __init__(self, name: str, payload: dict):
        self.name = name
        self._payload = payload
        self.budget = None

    async def fetch(self, **kwargs) -> dict:
        return self._payload

    async def healthcheck(self) -> bool:
        return True


class _Fail:
    def __init__(self, name: str):
        self.name = name
        self.budget = None

    async def fetch(self, **kwargs) -> dict:
        raise RuntimeError(f"{self.name} unavailable")

    async def healthcheck(self) -> bool:
        return False


def _key(**kwargs) -> str:
    return "f1:test:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


async def test_f1_sessions_chain_first_adapter_wins():
    chain = FallbackChain(
        name="f1:sessions",
        adapters=[_OK("openf1", {"sessions": [{"session_key": 9158}]}), _Fail("jolpica")],
        cache_key_fn=_key,
        fresh_ttl=21600,
        stale_ttl=86400,
    )
    result = await chain.fetch(year=2024)
    assert result.source == "openf1"
    assert result.value["sessions"][0]["session_key"] == 9158
    assert result.fallback_used is False


async def test_f1_sessions_chain_falls_back_to_jolpica():
    chain = FallbackChain(
        name="f1:sessions",
        adapters=[_Fail("openf1"), _OK("jolpica", {"sessions": [{"round": 1, "country": "Bahrain"}]})],
        cache_key_fn=_key,
        fresh_ttl=21600,
        stale_ttl=86400,
    )
    result = await chain.fetch(year=2024)
    assert result.source == "jolpica"
    assert result.fallback_used is True
    assert result.value["sessions"][0]["country"] == "Bahrain"


async def test_f1_laps_chain_falls_back_to_fastf1():
    chain = FallbackChain(
        name="f1:laps",
        adapters=[
            _Fail("openf1"),
            _OK("fastf1", {"laps": [{"lap_number": 1, "lap_duration": 91.234}]}),
        ],
        cache_key_fn=_key,
        fresh_ttl=3600,
        stale_ttl=86400,
    )
    result = await chain.fetch(session_key=9158, driver_number=1)
    assert result.source == "fastf1"
    assert result.fallback_used is True
    assert result.value["laps"][0]["lap_number"] == 1


async def test_f1_standings_chain_first_adapter_wins():
    chain = FallbackChain(
        name="f1:standings",
        adapters=[
            _OK("jolpica", {"standings": [{"position": 1, "driver": "Verstappen", "points": 575}]}),
            _Fail("fastf1"),
        ],
        cache_key_fn=_key,
        fresh_ttl=86400,
        stale_ttl=604800,
    )
    result = await chain.fetch(year=2024)
    assert result.source == "jolpica"
    assert result.fallback_used is False
    assert result.value["standings"][0]["driver"] == "Verstappen"


async def test_f1_chain_raises_when_all_fail():
    chain = FallbackChain(
        name="f1:laps",
        adapters=[_Fail("openf1"), _Fail("fastf1")],
        cache_key_fn=_key,
        fresh_ttl=3600,
    )
    with pytest.raises(AllSourcesFailedError) as exc:
        await chain.fetch(session_key=9158, driver_number=1)
    assert len(exc.value.attempts) == 2
    assert all(a["status"] == "error" for a in exc.value.attempts)


async def test_f1_laps_chain_keys_by_session_and_driver():
    from sportiq.f1 import chains

    key_a = chains.f1_laps_chain.cache_key_fn(session_key=9158, driver_number=1)
    key_b = chains.f1_laps_chain.cache_key_fn(session_key=9158, driver_number=44)
    key_c = chains.f1_laps_chain.cache_key_fn(session_key=9999, driver_number=1)
    assert key_a != key_b
    assert key_a != key_c
    assert "9158" in key_a
    assert "1" in key_a
    assert "44" in key_b
    assert "9999" in key_c


async def test_f1_weather_chain_keys_by_session():
    from sportiq.f1 import chains

    key_a = chains.f1_weather_chain.cache_key_fn(session_key=9158)
    key_b = chains.f1_weather_chain.cache_key_fn(session_key=9999)
    assert key_a != key_b
    assert "9158" in key_a
    assert "9999" in key_b
