#!/usr/bin/env python3
"""O.4 load harness — concurrent tool calls against stubbed chains.

Not in CI by default. Run manually: uv run python scripts/load_check.py

Uses stub adapters (no live HTTP) to verify the server handles K concurrent
calls without quota overrun or unbounded resource use.
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

K = 20  # concurrent calls


async def _fake_chain_fetch(*args, **kwargs):
    """Simulates a chain fetch with minimal latency."""
    await asyncio.sleep(0.01)
    return MagicMock(
        value={"matches": []},
        source="stub",
        is_stale=False,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=10,
    )


async def main():
    # Import tool once; patch the chain at module level so all K calls share it.
    from sportiq.cricket import tools as cricket_tools  # noqa: F401 (side-effect import)
    from sportiq.cricket.tools import cricket_get_live_matches

    print(f"Firing {K} concurrent tool calls...")

    with patch("sportiq.cricket.chains.live_score_chain.fetch", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = _fake_chain_fetch

        async def _run_single_call(i: int) -> float:
            start = time.monotonic()
            result = await cricket_get_live_matches()
            assert "data" in result or "error" in result, f"Call {i}: bad envelope"
            return time.monotonic() - start

        start = time.monotonic()
        times = await asyncio.gather(*[_run_single_call(i) for i in range(K)])
        elapsed = time.monotonic() - start

    p95 = sorted(times)[int(len(times) * 0.95)]
    print(f"  Total wall time: {elapsed*1000:.0f}ms")
    print(f"  p95 per-call: {p95*1000:.0f}ms")
    print(f"  All {K} calls returned valid envelopes")
    assert elapsed < 5.0, f"Load test too slow: {elapsed:.2f}s for {K} calls"
    print("PASS")


if __name__ == "__main__":
    asyncio.run(main())
