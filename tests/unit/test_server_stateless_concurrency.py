"""Stateless HTTP: overlapping requests must not close the shared cache/client.

Regression for the per-request FastMCP lifespan teardown (audit P0-2): stateless
mode enters `_lifespan` once per request, so closing the singletons there broke
any request still in flight with `'NoneType' object has no attribute 'set'`.
"""

from __future__ import annotations

import asyncio
import json

import httpx

MCP_HEADERS = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
}


class _SlowDriversAdapter:
    name = "stub_slow_drivers"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        await asyncio.sleep(0.3)
        return {"drivers": [{"driver_number": 1}]}

    async def healthcheck(self) -> bool:
        return True


def _sse_data(text: str) -> dict:
    for line in text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[len("data:") :].strip())
    raise AssertionError(f"no SSE data line in response: {text!r}")


async def test_stateless_overlapping_requests_keep_cache_open(monkeypatch):
    from sportiq.core.cache import get_cache
    from sportiq.f1.chains import f1_drivers_chain
    from sportiq.server import build_http_app, mcp

    monkeypatch.setenv("SPORTIQ_TRANSPORT", "http")
    monkeypatch.setattr(mcp, "_session_manager", None)
    app = build_http_app()
    original_adapters = f1_drivers_chain.adapters
    f1_drivers_chain.adapters = [_SlowDriversAdapter()]
    try:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:

                async def call_tool() -> httpx.Response:
                    return await client.post(
                        "/mcp",
                        headers=MCP_HEADERS,
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {
                                "name": "f1_get_drivers",
                                "arguments": {"session_key": 9999},
                            },
                        },
                    )

                async def list_tools(request_id: int) -> httpx.Response:
                    await asyncio.sleep(0.05)
                    return await client.post(
                        "/mcp",
                        headers=MCP_HEADERS,
                        json={"jsonrpc": "2.0", "id": request_id, "method": "tools/list"},
                    )

                tool_resp, *_ = await asyncio.gather(call_tool(), list_tools(2), list_tools(3))

            result = _sse_data(tool_resp.text)["result"]
            assert result.get("isError") is not True
            assert "Error executing tool" not in json.dumps(result)
            assert get_cache()._disk is not None
    finally:
        f1_drivers_chain.adapters = original_adapters


async def test_healthz_returns_ok_without_touching_cache(monkeypatch):
    from sportiq.core import cache as cache_module
    from sportiq.server import build_http_app, mcp

    def _boom():
        raise AssertionError("/healthz must not touch the cache")

    monkeypatch.setattr(mcp, "_session_manager", None)
    app = build_http_app()
    monkeypatch.setattr(cache_module, "get_cache", _boom)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/healthz")

    assert resp.status_code == 200
    assert resp.text == "ok"
