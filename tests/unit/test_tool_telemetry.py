"""tool_telemetry wraps each tool to emit one `tool_call` event per call.

The event is the only place that knows which tool ran, whether it *actually*
succeeded (MCP errors are HTTP 200), how long it took, and which client called
it. We assert the wrapper classifies ok / error-envelope / exception correctly
and never alters the tool's return value.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import ClassVar

import pytest

from sportiq.core import tool_telemetry


class _Recorder:
    """Stand-in for the structlog logger; records (method, event, fields)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def info(self, event: str, **kw: object) -> None:
        self.calls.append(("info", event, kw))

    def warning(self, event: str, **kw: object) -> None:
        self.calls.append(("warning", event, kw))

    def error(self, event: str, **kw: object) -> None:
        self.calls.append(("error", event, kw))


@pytest.fixture
def rec(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    r = _Recorder()
    monkeypatch.setattr(tool_telemetry, "_log", r)
    return r


async def test_success_envelope_logs_ok_and_passes_value_through(rec: _Recorder):
    async def fn(**kw):
        return {"data": {"x": 1}, "meta": {"source": "openfootball", "is_stale": True}}

    wrapped = tool_telemetry._instrument("football_get_fixtures", fn, asyncio.Semaphore(2))
    result = await wrapped()

    assert result == {"data": {"x": 1}, "meta": {"source": "openfootball", "is_stale": True}}
    method, event, fields = rec.calls[0]
    assert (method, event) == ("info", "tool_call")
    assert fields["tool"] == "football_get_fixtures"
    assert fields["success"] is True
    assert fields["outcome"] == "ok"
    assert fields["source"] == "openfootball"
    assert fields["is_stale"] is True
    assert isinstance(fields["latency_ms"], float)


async def test_error_envelope_logs_failure_with_code(rec: _Recorder):
    async def fn(**kw):
        return {"error": {"code": "ALL_SOURCES_FAILED", "message": "nope"}}

    wrapped = tool_telemetry._instrument("cricket_get_scorecard", fn, asyncio.Semaphore(2))
    await wrapped()

    method, event, fields = rec.calls[0]
    assert (method, event) == ("warning", "tool_call")
    assert fields["success"] is False
    assert fields["outcome"] == "error"
    assert fields["error"] == "ALL_SOURCES_FAILED"


async def test_exception_logs_and_reraises(rec: _Recorder):
    async def fn(**kw):
        raise ValueError("boom")

    wrapped = tool_telemetry._instrument("f1_predict_pit_strategy", fn, asyncio.Semaphore(2))
    with pytest.raises(ValueError):
        await wrapped()

    method, event, fields = rec.calls[0]
    assert (method, event) == ("error", "tool_call")
    assert fields["success"] is False
    assert fields["outcome"] == "exception"
    assert fields["error"] == "ValueError"


async def test_tool_telemetry_logs_scrubbed_exception_detail_and_frame(rec: _Recorder):
    async def fn(**kw):
        raise RuntimeError("boom apikey=SECRET123")

    wrapped = tool_telemetry._instrument("f1_get_drivers", fn, asyncio.Semaphore(2))
    with pytest.raises(RuntimeError):
        await wrapped()

    _, _, fields = rec.calls[0]
    assert fields["error"] == "RuntimeError"
    assert "boom" in fields["error_detail"]
    assert "SECRET123" not in fields["error_detail"]
    assert re.match(r".+\.py:\d+ \w+", fields["error_frame"])


async def test_tool_deadline_returns_upstream_timeout_envelope(
    rec: _Recorder, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(tool_telemetry.settings, "tool_deadline_seconds", 0.05)

    async def fn(**kw):
        await asyncio.sleep(1)
        return {"data": {}, "meta": {}}

    wrapped = tool_telemetry._instrument("football_get_fixtures", fn, asyncio.Semaphore(2))
    started = time.perf_counter()
    result = await wrapped()
    elapsed = time.perf_counter() - started

    assert result["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert result["error"]["retry_after_seconds"] == 60
    _, _, fields = rec.calls[0]
    assert fields["outcome"] == "error"
    assert fields["error"] == "UPSTREAM_TIMEOUT"
    assert elapsed < 0.5


async def test_tool_deadline_includes_semaphore_wait(
    rec: _Recorder, monkeypatch: pytest.MonkeyPatch
):
    # Each call's own work (0.15 s) fits the 0.2 s deadline; only the queued
    # second call, which first waits ~0.15 s for the single slot, overruns it.
    monkeypatch.setattr(tool_telemetry.settings, "tool_deadline_seconds", 0.2)

    async def fn(**kw):
        await asyncio.sleep(0.15)
        return {"data": {}, "meta": {}}

    wrapped = tool_telemetry._instrument("football_simulate_bracket", fn, asyncio.Semaphore(1))
    first, second = await asyncio.gather(wrapped(), wrapped())

    assert "data" in first
    assert second["error"]["code"] == "UPSTREAM_TIMEOUT"


def test_instrument_tools_wraps_only_async_tools():
    class _Tool:
        def __init__(self, name, fn, is_async):
            self.name, self.fn, self.is_async = name, fn, is_async

    async def a():
        return {"data": 1}

    def b():
        return {"data": 2}

    async_tool, sync_tool = _Tool("a", a, True), _Tool("b", b, False)

    class _Mgr:
        _tools: ClassVar = {"a": async_tool, "b": sync_tool}

    class _Mcp:
        _tool_manager = _Mgr()

    tool_telemetry.instrument_tools(_Mcp())
    assert async_tool.fn is not a  # wrapped
    assert sync_tool.fn is b  # untouched


async def test_expensive_tools_share_configured_concurrency_limit(rec: _Recorder):
    active = 0
    peak = 0
    two_entered = asyncio.Event()
    release = asyncio.Event()

    async def probe(**kw):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == 2:
            two_entered.set()
        await release.wait()
        active -= 1
        return {"data": {}, "meta": {}}

    wrapped = tool_telemetry._instrument("football_simulate_bracket", probe, asyncio.Semaphore(2))
    tasks = [asyncio.create_task(wrapped()) for _ in range(4)]

    await asyncio.wait_for(two_entered.wait(), timeout=1)
    await asyncio.sleep(0)
    assert peak == 2
    release.set()
    await asyncio.gather(*tasks)
    assert peak == 2


async def test_cheap_tools_are_not_serialized_by_expensive_limit(rec: _Recorder):
    active = 0
    peak = 0
    four_entered = asyncio.Event()
    release = asyncio.Event()

    async def probe(**kw):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == 4:
            four_entered.set()
        await release.wait()
        active -= 1
        return {"data": {}, "meta": {}}

    wrapped = tool_telemetry._instrument("football_get_fixtures", probe, asyncio.Semaphore(2))
    tasks = [asyncio.create_task(wrapped()) for _ in range(4)]

    await asyncio.wait_for(four_entered.wait(), timeout=1)
    assert peak == 4
    release.set()
    await asyncio.gather(*tasks)


def test_instrument_tools_wrapped_every_registered_tool():
    # Guard: instrument_tools silently no-ops if FastMCP's private registry moves
    # (SDK v2 renames it). The public list and the wrapped registry must agree.
    import sportiq.server as server

    registry = server.mcp._tool_manager._tools
    listed = asyncio.run(server.mcp.list_tools())
    assert len(registry) == len(listed) == 46
    unwrapped = [name for name, tool in registry.items() if not hasattr(tool.fn, "__wrapped__")]
    assert unwrapped == []
