"""Per-request Pro-key extraction for the hosted ``/mcp`` (pure ASGI).

Pulls the caller's Pro key off each HTTP request and binds it to the entitlement
contextvar for the downstream MCP handler, so the gate validates *this user's*
key (V2a). Two transports, checked in order:

  (A) URL path  ``…/u/<key>/mcp``  → the key is a path segment; we extract it and
      rewrite the path to ``/mcp`` so the MCP app routes normally. Universal:
      works with any client that accepts a connector URL (claude.ai web, ChatGPT).
  (B) ``Authorization: Bearer <key>`` header → for clients that send custom
      headers (Claude Desktop, IDEs).

No key on the request → nothing is bound; the gate then locks the paid tools (or,
locally, falls back to the env var). Pure ASGI, NOT ``BaseHTTPMiddleware`` —
BaseHTTPMiddleware buffers SSE and breaks the MCP streamable-HTTP transport (see
core/client_info.py for the full rationale). The contextvar is reset after every
request so a key never leaks across requests on a reused worker task.
"""

from __future__ import annotations

import re
from urllib.parse import unquote

from sportiq.core.entitlements import reset_request_key, set_request_key

# /u/<key>/mcp  (optional trailing slash). <key> is a single path segment.
_PATH_KEY = re.compile(r"^/u/([^/]+)/mcp/?$")


def _header(headers: list[tuple[bytes, bytes]], name: bytes) -> str:
    return next((v.decode("latin-1") for k, v in headers if k.lower() == name), "")


def _extract_key(scope: dict) -> str | None:
    """Return the request's Pro key (path or header), rewriting a ``/u/<key>/mcp``
    path back to ``/mcp`` as a side effect. None when no key is present."""
    path = scope.get("path", "")
    m = _PATH_KEY.match(path)
    if m:
        key = unquote(m.group(1)).strip()
        # Rewrite so the MCP app (mounted at /mcp) routes normally.
        scope["path"] = "/mcp"
        scope["raw_path"] = b"/mcp"
        return key or None
    auth = _header(scope.get("headers", []), b"authorization")
    if auth[:7].lower() == "bearer ":
        return auth[7:].strip() or None
    return None


class ProKeyMiddleware:
    """Bind the per-request Pro key to the entitlement contextvar (HTTP only)."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        key = _extract_key(scope)
        if key is None:
            await self.app(scope, receive, send)
            return
        token = set_request_key(key)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_request_key(token)
