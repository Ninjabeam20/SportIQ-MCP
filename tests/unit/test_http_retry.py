"""get_json retry policy — 5xx and transport errors retry; 4xx fails fast.

Retrying a 401/403/404/429 would burn 3x the upstream quota on a guaranteed
failure, so only server-side faults (5xx) and transport errors are transient.
"""
from __future__ import annotations

import httpx
import pytest
import respx
from httpx import Response

from sportiq.core.http import get_json, get_json_burst

_URL = "https://example.test/data"


@respx.mock
async def test_get_json_does_not_retry_on_429():
    route = respx.get(_URL).mock(return_value=Response(429))
    with pytest.raises(httpx.HTTPStatusError):
        await get_json(_URL)
    assert route.call_count == 1


@respx.mock
async def test_get_json_does_not_retry_on_401():
    route = respx.get(_URL).mock(return_value=Response(401))
    with pytest.raises(httpx.HTTPStatusError):
        await get_json(_URL)
    assert route.call_count == 1


@respx.mock
async def test_get_json_retries_on_503():
    route = respx.get(_URL).mock(return_value=Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        await get_json(_URL)
    assert route.call_count == 3


@respx.mock
async def test_get_json_retries_on_transport_error():
    route = respx.get(_URL).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(httpx.ConnectError):
        await get_json(_URL)
    assert route.call_count == 3


@respx.mock
async def test_get_json_burst_retries_on_429():
    """OpenF1 has no daily quota; its 429 is a transient burst signal, so the
    burst variant backs off and retries (up to 4 attempts)."""
    route = respx.get(_URL).mock(return_value=Response(429))
    with pytest.raises(httpx.HTTPStatusError):
        await get_json_burst(_URL)
    assert route.call_count == 4


@respx.mock
async def test_get_json_burst_recovers_after_429():
    """A 429 then a 200 → burst fetch returns the eventual success."""
    route = respx.get(_URL).mock(
        side_effect=[Response(429), Response(200, json={"ok": True})]
    )
    result = await get_json_burst(_URL)
    assert result == {"ok": True}
    assert route.call_count == 2
