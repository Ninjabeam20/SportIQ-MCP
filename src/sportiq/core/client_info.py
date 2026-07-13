"""Lightweight MCP client-identification logging (HTTP transport only).

Emits one structured log line per request to ``/mcp`` recording the calling
client — both the raw HTTP ``User-Agent`` and, when present, the MCP
``clientInfo.name``/``version`` from an ``initialize`` request body. The local
analytics dashboard (``scripts/dashboard.py``) reads these from Cloud Logging to
break usage down by AI client (Claude / ChatGPT / IDE / …).

No PII: only the client's self-reported name/version and User-Agent are logged,
and structlog's redaction processor scrubs any secret-shaped strings. The server
remains anonymous — this identifies the *software*, never the user.

Implemented as a pure ASGI middleware, NOT Starlette's ``BaseHTTPMiddleware``:
BaseHTTPMiddleware buffers/breaks the SSE streaming responses the MCP
streamable-HTTP transport relies on, and reading ``request.body()`` there
consumes the receive stream so the downstream MCP handler sees an empty body
(canary 2026-06-12: HTTP 200 with no payload). This version *tees* body chunks
as the downstream app itself reads them — nothing is consumed, the response
passes through untouched.

Attached to the Starlette app only on the streamable-HTTP transport; the stdio
path (local single-client uvx usage) never sees this.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any

import structlog

from sportiq.core.logging import get_logger

_log = get_logger("client_info")

# session_id -> clean MCP clientInfo.name, captured at `initialize`. MCP assigns
# the session id in the *initialize response* (Mcp-Session-Id header) and the
# client echoes it on every later request — but the clean client name only
# appears in the initialize *body*. We bridge the two so each `tools/call` can be
# attributed to a client. Bounded LRU; on a cache miss (e.g. the initialize hit a
# different Cloud Run instance) attribution falls back to the User-Agent, which
# the dashboard classifies. Enabling Cloud Run session affinity (free) keeps a
# session pinned to one instance and maximises hits.
_SESSION_CLIENT: OrderedDict[str, str] = OrderedDict()
_MAX_SESSIONS = 4096
_MAX_CAPTURE_BYTES = 64 * 1024


def _sanitize_field(value: Any, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(char for char in value if char.isprintable()).strip()[:max_length]


def _remember_session(session_id: str, name: str | None) -> None:
    if not session_id or not name:
        return
    _SESSION_CLIENT[session_id] = name
    _SESSION_CLIENT.move_to_end(session_id)
    while len(_SESSION_CLIENT) > _MAX_SESSIONS:
        _SESSION_CLIENT.popitem(last=False)


def _header(headers: list[tuple[bytes, bytes]], name: bytes) -> str:
    return next((v.decode("latin-1") for k, v in headers if k.lower() == name), "")


def _extract_client_info(body: bytes) -> dict[str, Any] | None:
    """Pull ``clientInfo`` out of an MCP ``initialize`` JSON-RPC body, if present.

    Returns ``None`` for any non-initialize / unparseable body — the common case
    (every tool call) — so the hot path stays cheap.
    """
    if not body:
        return None
    try:
        msg = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(msg, dict) or msg.get("method") != "initialize":
        return None
    info = (msg.get("params") or {}).get("clientInfo")
    if isinstance(info, dict):
        return {
            "name": _sanitize_field(info.get("name"), 100),
            "version": _sanitize_field(info.get("version"), 100),
        }
    return None


class ClientInfoMiddleware:
    """Log the calling client for each ``/mcp`` request (pure ASGI pass-through).

    On an ``initialize`` request it logs the rich MCP ``clientInfo``; on every
    request it logs the ``User-Agent`` as a fallback signal. One line per
    request, ``event="mcp_request"``.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not scope["path"].rstrip("/").endswith("/mcp"):
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers", [])
        user_agent = _sanitize_field(_header(headers, b"user-agent"), 300)
        # On a tools/call the session id is already established → look up the
        # clean client name captured at initialize. None on initialize itself
        # (no session yet) and on cache misses; the dashboard then classifies the
        # User-Agent instead.
        session_id = _header(headers, b"mcp-session-id")
        client_name = _SESSION_CLIENT.get(session_id) if session_id else None

        # Bind for the whole downstream call so every log line in this request —
        # crucially the `tool_call` events — carries who is calling. Same asyncio
        # task, so contextvars propagate into the tool handler.
        with structlog.contextvars.bound_contextvars(
            client_name=client_name, user_agent=user_agent
        ):
            if scope.get("method") != "POST":
                _log.info(
                    "mcp_request",
                    user_agent=user_agent,
                    client_name=client_name,
                    client_version=None,
                )
                await self.app(scope, receive, send)
                return

            captured = bytearray()
            logged = False
            init_name: str | None = None

            def _emit(body: bytes) -> None:
                nonlocal logged, init_name
                logged = True
                info = _extract_client_info(body)
                if info:
                    init_name = info.get("name")
                _log.info(
                    "mcp_request",
                    user_agent=user_agent,
                    client_name=(info or {}).get("name") or client_name,
                    client_version=(info or {}).get("version"),
                )

            async def tee_receive() -> dict[str, Any]:
                # Forward messages unchanged; copy body bytes as the downstream
                # MCP handler reads them. Nothing is consumed ahead of the handler.
                message = await receive()
                if message["type"] == "http.request":
                    remaining = _MAX_CAPTURE_BYTES - len(captured)
                    if remaining > 0:
                        captured.extend(message.get("body", b"")[:remaining])
                    if not message.get("more_body") and not logged:
                        _emit(bytes(captured))
                return message

            async def tee_send(message: dict[str, Any]) -> None:
                # Pure pass-through; only *peek* at the response start to learn the
                # session id MCP assigned for an initialize, and map it to the
                # client name from the body. Never buffers — SSE streams untouched.
                if message["type"] == "http.response.start" and init_name:
                    sid = _header(message.get("headers", []), b"mcp-session-id")
                    _remember_session(sid, init_name)
                await send(message)

            await self.app(scope, tee_receive, tee_send)
            if not logged:  # downstream rejected before reading the body
                _emit(b"")
