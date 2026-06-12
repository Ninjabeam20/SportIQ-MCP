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
from typing import Any

from sportiq.core.logging import get_logger

_log = get_logger("client_info")


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
        return {"name": info.get("name"), "version": info.get("version")}
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

        user_agent = next(
            (v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"user-agent"),
            "",
        )

        if scope.get("method") != "POST":
            _log.info("mcp_request", user_agent=user_agent, client_name=None, client_version=None)
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        logged = False

        def _emit(body: bytes) -> None:
            nonlocal logged
            logged = True
            info = _extract_client_info(body)
            _log.info(
                "mcp_request",
                user_agent=user_agent,
                client_name=(info or {}).get("name"),
                client_version=(info or {}).get("version"),
            )

        async def tee_receive() -> dict[str, Any]:
            # Forward messages unchanged; copy body bytes as the downstream MCP
            # handler reads them. Nothing is consumed ahead of the handler.
            message = await receive()
            if message["type"] == "http.request":
                chunks.append(message.get("body", b""))
                if not message.get("more_body") and not logged:
                    _emit(b"".join(chunks))
            return message

        await self.app(scope, tee_receive, send)
        if not logged:  # downstream rejected before reading the body
            _emit(b"")
