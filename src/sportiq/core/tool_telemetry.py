"""Per-tool-call telemetry — the signal Cloud Run's HTTP metrics can't give.

MCP tool failures return HTTP 200 (the error lives in the JSON envelope), so the
Cloud Run ``request_count`` 2xx panel counts a failed tool call as a success and
has no notion of *which* tool ran or how long *it* took. This module emits one
structured ``tool_call`` log line per invocation::

    {"event": "tool_call", "tool": "football_simulate_bracket",
     "success": true, "outcome": "ok", "latency_ms": 1234.5,
     "source": "openfootball", "is_stale": false,
     "client_name": "claude", "user_agent": "..."}

``client_name`` / ``user_agent`` ride along automatically from the request
contextvars bound by :class:`~sportiq.core.client_info.ClientInfoMiddleware`
(``merge_contextvars`` is already in the structlog pipeline). From these lines
the local dashboard builds: calls by tool, error rate by tool, latency by tool,
calls by client, and the client-x-tool matrix.

Wiring mirrors ``apply_param_descriptions``: walk the FastMCP tool registry once
at startup and wrap each tool's ``fn``. ``Tool.run`` calls ``self.fn`` via the
cached ``fn_metadata`` (arg validation uses a cached model, *not* the live
signature — verified against mcp 1.x), so replacing ``tool.fn`` with a wrapper
is safe and touches none of the 44 tool source files.
"""

from __future__ import annotations

import asyncio
import functools
import time
import traceback
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from sportiq.config import settings
from sportiq.core.logging import get_logger
from sportiq.core.redact import scrub
from sportiq.core.tool_response import error_envelope

_log = get_logger("tool_telemetry")

_EXPENSIVE_TOOLS = frozenset(
    {
        "football_simulate_group",
        "football_simulate_bracket",
        "football_knockout_path",
        "f1_predict_pit_strategy",
        "cricket_build_dream11_team",
    }
)


def instrument_tools(mcp: Any) -> None:
    """Wrap every registered async tool to emit a ``tool_call`` event.

    No-op if the FastMCP private registry has moved (degrades to no telemetry
    rather than crashing startup — same defensive stance as param_docs).
    """
    tools = getattr(getattr(mcp, "_tool_manager", None), "_tools", None)
    if not tools:
        return
    expensive_semaphore = asyncio.Semaphore(settings.expensive_tool_concurrency)
    for tool in tools.values():
        if getattr(tool, "is_async", False):
            tool.fn = _instrument(tool.name, tool.fn, expensive_semaphore)


def _instrument(
    name: str,
    fn: Callable[..., Awaitable[Any]],
    expensive_semaphore: asyncio.Semaphore,
) -> Callable[..., Awaitable[Any]]:
    @functools.wraps(fn)
    async def wrapper(**kwargs: Any) -> Any:
        start = time.perf_counter()
        deadline = settings.tool_deadline_seconds

        async def _call() -> Any:
            if name in _EXPENSIVE_TOOLS:
                async with expensive_semaphore:
                    return await fn(**kwargs)
            return await fn(**kwargs)

        try:
            # The deadline covers the semaphore wait too. Work offloaded with
            # asyncio.to_thread keeps running after the deadline (threads can't be
            # cancelled); only the caller stops waiting.
            result = await asyncio.wait_for(_call(), timeout=deadline)
        except TimeoutError:
            result = error_envelope(
                code="UPSTREAM_TIMEOUT",
                message=f"{name} exceeded the {deadline:g}s tool deadline.",
                retry_after_seconds=60,
                suggestion="Retry shortly; upstream sources were slow or a simulation was queued.",
            )
        except Exception as exc:
            # An uncaught exception is the worst "bad": no envelope was returned.
            frames = traceback.extract_tb(exc.__traceback__)
            f = frames[-1] if frames else None
            _log.error(
                "tool_call",
                tool=name,
                success=False,
                outcome="exception",
                error=type(exc).__name__,
                error_detail=scrub(str(exc))[:300],
                error_frame=f"{Path(f.filename).name}:{f.lineno} {f.name}" if f else None,
                latency_ms=round((time.perf_counter() - start) * 1000, 1),
            )
            raise
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        err = result.get("error") if isinstance(result, dict) else None
        if err:
            # Tool returned an error envelope (HTTP 200 — invisible to Cloud Run).
            _log.warning(
                "tool_call",
                tool=name,
                success=False,
                outcome="error",
                error=err.get("code") if isinstance(err, dict) else None,
                latency_ms=latency_ms,
            )
        else:
            meta = (result.get("meta") or {}) if isinstance(result, dict) else {}
            _log.info(
                "tool_call",
                tool=name,
                success=True,
                outcome="ok",
                source=meta.get("source"),
                is_stale=bool(meta.get("is_stale", False)),
                latency_ms=latency_ms,
            )
        return result

    return wrapper
