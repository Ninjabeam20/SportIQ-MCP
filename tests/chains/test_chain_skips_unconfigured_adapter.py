"""Verify that opt-in adapters are silently skipped when disabled."""

from __future__ import annotations

from sportiq.core.errors import MissingCredentialsError
from sportiq.core.fallback import FallbackChain


class _DisabledAdapter:
    """Simulates an adapter that raises MissingCredentialsError (opt-in disabled)."""
    name = "disabled_adapter"
    call_count = 0

    async def fetch(self, **kwargs):
        self.call_count += 1
        raise MissingCredentialsError("adapter is disabled")

    async def healthcheck(self) -> bool:
        return False


class _FallbackAdapter:
    name = "fallback_adapter"

    async def fetch(self, **kwargs) -> dict:
        return {"matches": [{"id": "fallback"}]}

    async def healthcheck(self) -> bool:
        return True


async def test_disabled_adapter_is_walked_past():
    disabled = _DisabledAdapter()
    fallback = _FallbackAdapter()

    chain = FallbackChain(
        name="cricket:test",
        adapters=[disabled, fallback],
        cache_key_fn=lambda **_: "cricket:test:skip",
        fresh_ttl=30,
    )
    result = await chain.fetch()

    assert result.source == "fallback_adapter"
    assert result.fallback_used is True
    assert disabled.call_count == 1


async def test_attempt_log_includes_disabled_adapter_error():
    disabled = _DisabledAdapter()
    fallback = _FallbackAdapter()

    chain = FallbackChain(
        name="cricket:test",
        adapters=[disabled, fallback],
        cache_key_fn=lambda **_: "cricket:test:skip2",
        fresh_ttl=30,
    )
    result = await chain.fetch()

    assert result.attempts[0]["name"] == "disabled_adapter"
    assert result.attempts[0]["status"] == "error"
    assert "MissingCredentialsError" in result.attempts[0]["error"]
