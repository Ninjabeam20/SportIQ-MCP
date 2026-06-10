"""FallbackChain behavior for cricket chains — all adapters stubbed."""

from __future__ import annotations

import pytest

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.fallback import FallbackChain


class _OK:
    def __init__(self, name: str, payload: dict):
        self.name = name
        self._payload = payload

    async def fetch(self, **kwargs) -> dict:
        return self._payload

    async def healthcheck(self) -> bool:
        return True


class _Fail:
    def __init__(self, name: str, exc: Exception | None = None):
        self.name = name
        self._exc = exc or RuntimeError(f"{name} unavailable")

    async def fetch(self, **kwargs) -> dict:
        raise self._exc

    async def healthcheck(self) -> bool:
        return False


def _key(**kwargs) -> str:
    return "cricket:test:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


async def test_live_score_chain_first_adapter_wins():
    chain = FallbackChain(
        name="cricket:live_score",
        adapters=[_OK("cricapi", {"matches": [{"id": "m1"}]}), _Fail("ndtv")],
        cache_key_fn=_key,
        fresh_ttl=30,
        stale_ttl=300,
    )
    result = await chain.fetch()
    assert result.source == "cricapi"
    assert result.value["matches"][0]["id"] == "m1"
    assert result.fallback_used is False


async def test_live_score_chain_falls_back_on_primary_failure():
    chain = FallbackChain(
        name="cricket:live_score",
        adapters=[_Fail("cricapi"), _OK("ndtv", {"matches": [{"raw": "IND vs AUS"}]})],
        cache_key_fn=_key,
        fresh_ttl=30,
        stale_ttl=300,
    )
    result = await chain.fetch()
    assert result.source == "ndtv"
    assert result.fallback_used is True


async def test_squad_chain_falls_through_to_static_seed():
    chain = FallbackChain(
        name="cricket:squad",
        adapters=[
            _Fail("cricapi"),
            _OK("static_seed", {"players": [{"name": "Rohit Sharma"}], "team": "MI"}),
        ],
        cache_key_fn=_key,
        fresh_ttl=43200,
        stale_ttl=259200,
    )
    result = await chain.fetch(team="MI")
    assert result.source == "static_seed"
    assert result.fallback_used is True
    assert result.value["players"][0]["name"] == "Rohit Sharma"


async def test_chain_raises_when_all_fail_and_no_cache():
    chain = FallbackChain(
        name="cricket:live_score",
        adapters=[_Fail("cricapi"), _Fail("ndtv"), _Fail("cricbuzz"), _Fail("rapidapi")],
        cache_key_fn=_key,
        fresh_ttl=30,
    )
    with pytest.raises(AllSourcesFailedError) as exc:
        await chain.fetch()
    assert len(exc.value.attempts) == 4
    assert all(a["status"] == "error" for a in exc.value.attempts)


async def test_scorecard_chain_keys_by_match_id():
    from sportiq.cricket import chains

    key_abc = chains.scorecard_chain.cache_key_fn(match_id="abc")
    key_xyz = chains.scorecard_chain.cache_key_fn(match_id="xyz")
    assert key_abc != key_xyz
    assert "abc" in key_abc
    assert "xyz" in key_xyz


async def test_player_stats_chain_keys_by_player_id():
    from sportiq.cricket import chains

    a = chains.player_stats_chain.cache_key_fn(player_id="p1")
    b = chains.player_stats_chain.cache_key_fn(player_id="p2")
    assert a != b
    assert "p1" in a
    assert "p2" in b


async def test_hostile_user_args_are_hashed_in_cache_keys():
    """caching-policy.md: user-supplied strings that could contain `:` or `*`
    must not enter a cache key raw — a crafted arg could otherwise collide with
    another key namespace. Legit upstream ids (alnum/-/_) stay readable."""
    from sportiq.cricket import chains

    hostile = "ipl:2026:*"
    keys = [
        chains.standings_chain.cache_key_fn(series_id=hostile),
        chains.fixtures_chain.cache_key_fn(series_id=hostile),
        chains.scorecard_chain.cache_key_fn(match_id=hostile),
        chains.player_stats_chain.cache_key_fn(player_id=hostile),
    ]
    for key in keys:
        assert hostile not in key
        assert "*" not in key
        # prefix stays intact: sportiq:cricket:<category>:<hashed-arg>
        assert key.startswith("sportiq:cricket:")
    assert len(set(keys)) == len(keys)  # distinct categories stay distinct


async def test_player_stats_chain_falls_through_to_rapidapi():
    chain = FallbackChain(
        name="cricket:player_stats",
        adapters=[
            _Fail("cricapi"),
            _OK("rapidapi_cricbuzz", {"values": [{"name": "T20I", "runs": "4008"}]}),
        ],
        cache_key_fn=lambda player_id, **_: f"sportiq:cricket:player_stats:{player_id}",
        fresh_ttl=86400,
        stale_ttl=604800,
    )
    result = await chain.fetch(player_id="p_kohli_001")
    assert result.source == "rapidapi_cricbuzz"
    assert result.fallback_used is True
    assert result.value["values"][0]["runs"] == "4008"


async def test_chain_serves_stale_when_all_fail():
    chain = FallbackChain(
        name="cricket:live_score",
        adapters=[_OK("cricapi", {"matches": [{"id": "stale"}]})],
        cache_key_fn=_key,
        fresh_ttl=0,
        stale_ttl=3600,
    )
    await chain.fetch()

    chain.adapters = [_Fail("cricapi")]
    result = await chain.fetch()
    assert result.is_stale is True
    assert result.source.startswith("cache:stale:")
    assert result.value["matches"][0]["id"] == "stale"
