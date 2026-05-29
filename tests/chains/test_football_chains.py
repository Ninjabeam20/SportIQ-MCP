"""FallbackChain behavior for football chains — network adapters stubbed."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

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
    return "football:test:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


async def test_fixtures_chain_first_adapter_wins():
    chain = FallbackChain(
        name="football:fixtures",
        adapters=[_OK("api_football", {"fixtures": [{"home": "ARG"}]}), _Fail("football_data_org")],
        cache_key_fn=_key,
        fresh_ttl=21600,
        stale_ttl=86400,
    )
    result = await chain.fetch()
    assert result.source == "api_football"
    assert result.fallback_used is False


async def test_fixtures_chain_falls_back_to_static_seed():
    chain = FallbackChain(
        name="football:fixtures",
        adapters=[
            _Fail("api_football"),
            _Fail("football_data_org"),
            _OK("static_seed", {"fixtures": [{"home": "Argentina", "away": "Mexico"}]}),
        ],
        cache_key_fn=_key,
        fresh_ttl=21600,
        stale_ttl=86400,
    )
    result = await chain.fetch()
    assert result.source == "static_seed"
    assert result.fallback_used is True
    # Same output shape as the primary adapter — the discipline lesson.
    assert "fixtures" in result.value


async def test_chain_raises_when_all_fail():
    chain = FallbackChain(
        name="football:standings",
        adapters=[_Fail("api_football"), _Fail("football_data_org")],
        cache_key_fn=_key,
        fresh_ttl=600,
    )
    with pytest.raises(AllSourcesFailedError) as exc:
        await chain.fetch()
    assert len(exc.value.attempts) == 2


async def test_groups_chain_static_terminator_returns_draw_and_ratings():
    from sportiq.football import chains

    result = await chains.football_groups_chain.fetch()
    assert len(result.value["groups"]) == 12
    assert len(result.value["ratings"]) == 48
    assert result.value["format"]["best_thirds"] == 8


async def test_squad_chain_keys_by_team():
    from sportiq.football import chains

    key_a = chains.football_squad_chain.cache_key_fn(team="ARG")
    key_b = chains.football_squad_chain.cache_key_fn(team="BRA")
    assert key_a != key_b
    assert "ARG" in key_a


@respx.mock
async def test_squad_chain_empty_api_football_falls_through_to_seed(monkeypatch):
    # A1: with a key set but api_football returning an empty squad (country code
    # vs numeric id), the chain must walk past to the static seed, not stop.
    from sportiq.config import settings
    from sportiq.football import chains

    monkeypatch.setattr(settings, "apifootball_key", "test-key")
    respx.get("https://v3.football.api-sports.io/players/squads").mock(
        return_value=Response(200, json={"response": []})
    )
    result = await chains.football_squad_chain.fetch(team="ARG")
    assert result.source == "static_seed"
    assert result.value["team"] == "ARG"
