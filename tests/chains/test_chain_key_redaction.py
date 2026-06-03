"""Regression: an upstream error carrying an API key must never leak the key
into FallbackChain.attempts or the error envelope's sources_tried."""
from __future__ import annotations

import httpx
import pytest

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.fallback import FallbackChain
from sportiq.core.tool_response import error_envelope

_SECRET = "SUPERSECRETKEY999"
_LEAKY_URL = f"https://api.cricapi.com/v1/currentMatches?apikey={_SECRET}&offset=0"


class _LeakyAdapter:
    """Raises the exact httpx error shape that embeds the key-bearing URL."""

    name = "cricapi"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        request = httpx.Request("GET", _LEAKY_URL)
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError(
            f"Client error '401 Unauthorized' for url '{_LEAKY_URL}'",
            request=request,
            response=response,
        )

    async def healthcheck(self) -> bool:
        return True


def _key(**kwargs) -> str:
    return "redact_test:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


def _chain() -> FallbackChain:
    return FallbackChain(
        name="cricket:redact",
        adapters=[_LeakyAdapter()],
        cache_key_fn=_key,
        fresh_ttl=0,
        stale_ttl=0,
    )


async def test_chain_attempts_do_not_leak_the_api_key():
    with pytest.raises(AllSourcesFailedError) as exc_info:
        await _chain().fetch(match="x")

    serialized = str(exc_info.value.attempts)
    assert _SECRET not in serialized
    # The attempt was still recorded (redacted, not dropped).
    assert any(a.get("status") == "error" for a in exc_info.value.attempts)


async def test_error_envelope_sources_tried_do_not_leak_the_api_key():
    with pytest.raises(AllSourcesFailedError) as exc_info:
        await _chain().fetch(match="x")

    envelope = error_envelope(
        code="ALL_SOURCES_FAILED",
        message="all failed",
        sources_tried=exc_info.value.attempts,
    )
    assert _SECRET not in str(envelope)
