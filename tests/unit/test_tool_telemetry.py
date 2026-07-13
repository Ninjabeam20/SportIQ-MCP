"""tool_telemetry wraps each tool to emit one `tool_call` event per call.

The event is the only place that knows which tool ran, whether it *actually*
succeeded (MCP errors are HTTP 200), how long it took, and which client called
it. We assert the wrapper classifies ok / error-envelope / exception correctly
and never alters the tool's return value.
"""
from __future__ import annotations

import asyncio
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

    wrapped = tool_telemetry._instrument(
        "football_simulate_bracket", probe, asyncio.Semaphore(2)
    )
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

    wrapped = tool_telemetry._instrument(
        "football_get_fixtures", probe, asyncio.Semaphore(2)
    )
    tasks = [asyncio.create_task(wrapped()) for _ in range(4)]

    await asyncio.wait_for(four_entered.wait(), timeout=1)
    assert peak == 4
    release.set()
    await asyncio.gather(*tasks)
