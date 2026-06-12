"""Lightweight MCP client-identification logging (HTTP transport only).

Emits one structured log line per request to ``/mcp`` recording the calling
client — both the raw HTTP ``User-Agent`` and, when present, the MCP
``clientInfo.name``/``version`` from an ``initialize`` request body. The local
analytics dashboard (``scripts/dashboard.py``) reads these from Cloud Logging to
break usage down by AI client (Claude / ChatGPT / IDE / …).

No PII: only the client's self-reported name/version and User-Agent are logged,
and structlog's redaction processor scrubs any secret-shaped strings. The server
remains anonymous — this identifies the *software*, never the user.

Attached to the Starlette app only on the streamable-HTTP transport; the stdio
path (local single-client uvx usage) never sees this.
"""

from __future__ import annotations

import json
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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


class ClientInfoMiddleware(BaseHTTPMiddleware):
    """Log the calling client for each ``/mcp`` request.

    On an ``initialize`` request it logs the rich MCP ``clientInfo``; on every
    request it logs the ``User-Agent`` as a fallback signal. One line per
    request, ``event="mcp_request"``.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.rstrip("/").endswith("/mcp"):
            return await call_next(request)

        user_agent = request.headers.get("user-agent", "")
        client_info: dict[str, Any] | None = None

        # Reading the body here consumes the stream; re-prime it so the MCP
        # handler downstream can read it again. Only done for /mcp POSTs.
        if request.method == "POST":
            body = await request.body()
            client_info = _extract_client_info(body)

            async def _receive() -> dict[str, Any]:
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = _receive  # re-prime for the downstream handler

        _log.info(
            "mcp_request",
            user_agent=user_agent,
            client_name=(client_info or {}).get("name"),
            client_version=(client_info or {}).get("version"),
        )
        return await call_next(request)
