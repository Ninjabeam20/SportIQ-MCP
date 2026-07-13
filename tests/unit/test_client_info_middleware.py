"""ClientInfoMiddleware must be a transparent pass-through for the MCP
streamable-HTTP transport.

Regression for the 2026-06-12 canary failure: the original BaseHTTPMiddleware
implementation consumed the request body (downstream handler saw it empty) and
broke the SSE response — initialize returned HTTP 200 with no payload. This
exercises the real app + middleware in-process (no network).
"""
from __future__ import annotations

import json

import structlog
from starlette.testclient import TestClient

from sportiq.core import client_info
from sportiq.core.client_info import (
    ClientInfoMiddleware,
    _extract_client_info,
    _remember_session,
)

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "middleware-e2e", "version": "1.0"},
    },
}
_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def test_initialize_passes_through_middleware_with_full_body():
    from mcp.server.transport_security import TransportSecuritySettings

    from sportiq.server import mcp

    # Mirror main()'s HTTP branch: rebinding protection off (else the
    # TestClient "testserver" host is rejected before the handler runs).
    prior = mcp.settings.transport_security
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
    try:
        app = mcp.streamable_http_app()
        app.add_middleware(ClientInfoMiddleware)
        with TestClient(app) as client:
            resp = client.post("/mcp", json=_INIT, headers=_HEADERS)
    finally:
        mcp.settings.transport_security = prior

    assert resp.status_code == 200
    # SSE-framed JSON-RPC result must actually carry the serverInfo payload —
    # an empty body here is exactly the regression this test locks out.
    assert '"serverInfo"' in resp.text
    assert '"name":"sportiq"' in resp.text.replace(" ", "")


def test_extract_client_info_parses_initialize_only():
    assert _extract_client_info(json.dumps(_INIT).encode()) == {
        "name": "middleware-e2e",
        "version": "1.0",
    }
    assert _extract_client_info(b'{"method":"tools/list"}') is None
    assert _extract_client_info(b"not json") is None
    assert _extract_client_info(b"") is None


def test_remember_session_dedups_evicts_and_ignores_blanks(monkeypatch):
    monkeypatch.setattr(client_info, "_MAX_SESSIONS", 2)
    client_info._SESSION_CLIENT.clear()
    _remember_session("", "claude")  # blank id ignored
    _remember_session("s1", None)  # blank name ignored
    assert dict(client_info._SESSION_CLIENT) == {}
    _remember_session("s1", "claude")
    _remember_session("s2", "cursor")
    _remember_session("s3", "chatgpt")  # over cap -> oldest (s1) evicted
    assert "s1" not in client_info._SESSION_CLIENT
    assert client_info._SESSION_CLIENT["s3"] == "chatgpt"


async def _drive(mw, scope, body):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    sent: list[dict] = []

    async def send(message):
        sent.append(message)

    await mw(scope, receive, send)
    return sent


async def test_middleware_binds_client_to_contextvars_for_tool_calls():
    """A tools/call carries a session id → the bound client_name is the clean
    name captured at initialize, so tool_call events get attributed."""
    client_info._SESSION_CLIENT["sess-1"] = "claude"
    seen: dict = {}

    async def app(scope, receive, send):
        await receive()
        seen.update(structlog.contextvars.get_contextvars())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/mcp",
        "headers": [(b"user-agent", b"UA/1"), (b"mcp-session-id", b"sess-1")],
    }
    await _drive(ClientInfoMiddleware(app), scope, b'{"method":"tools/call"}')
    assert seen.get("client_name") == "claude"
    assert seen.get("user_agent") == "UA/1"


async def test_middleware_captures_session_id_from_initialize_response():
    """initialize: clean name is in the body, session id is in the *response*
    header — the send-tee bridges them into the session map."""
    client_info._SESSION_CLIENT.clear()

    async def app(scope, receive, send):
        await receive()
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"mcp-session-id", b"sess-xyz")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/mcp",
        "headers": [(b"user-agent", b"UA")],
    }
    await _drive(ClientInfoMiddleware(app), scope, json.dumps(_INIT).encode())
    assert client_info._SESSION_CLIENT.get("sess-xyz") == "middleware-e2e"


async def test_middleware_bounds_capture_but_forwards_large_body(monkeypatch):
    captured_lengths: list[int] = []
    original = client_info._extract_client_info

    def recording_extract(body: bytes):
        captured_lengths.append(len(body))
        return original(body)

    monkeypatch.setattr(client_info, "_extract_client_info", recording_extract)
    forwarded = bytearray()

    async def app(scope, receive, send):
        while True:
            message = await receive()
            forwarded.extend(message.get("body", b""))
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    body = b"x" * (70 * 1024)
    messages = [
        {"type": "http.request", "body": body[:40_000], "more_body": True},
        {"type": "http.request", "body": body[40_000:], "more_body": False},
    ]

    async def receive():
        return messages.pop(0)

    async def send(_message):
        return None

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/mcp",
        "headers": [(b"user-agent", b"UA")],
    }
    await ClientInfoMiddleware(app)(scope, receive, send)

    assert bytes(forwarded) == body
    assert captured_lengths == [64 * 1024]


def test_client_fields_are_sanitized_and_bounded():
    body = json.dumps(
        {
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "  bad\nname" + "x" * 200,
                    "version": "\t1.0\r",
                }
            },
        }
    ).encode()
    info = _extract_client_info(body)

    assert info is not None
    assert info["name"].startswith("badname")
    assert len(info["name"]) == 100
    assert info["version"] == "1.0"
