"""Legacy ``/u/<key>/mcp`` connector-path compatibility (pure ASGI).

The paid edition (≤0.2.3) accepted per-user keys as a URL path segment —
``…/u/<key>/mcp`` — and sponsors' AI connectors (claude.ai, ChatGPT) were
configured with that URL. The free edition removed the entitlement gate, which
also removed the path rewrite, so those connectors started 404ing. This
middleware restores just the rewrite: ``/u/<anything>/mcp`` routes to ``/mcp``
and the key segment is ignored (all tools are free).

Pure ASGI, NOT ``BaseHTTPMiddleware`` — BaseHTTPMiddleware buffers SSE and
breaks the MCP streamable-HTTP transport (see core/client_info.py).
"""

from __future__ import annotations

import re

# /u/<key>/mcp  (optional trailing slash). <key> is a single path segment.
_LEGACY_KEY_PATH = re.compile(r"^/u/([^/]+)/mcp/?$")


class LegacyKeyPathMiddleware:
    """Rewrite legacy ``/u/<key>/mcp`` paths to ``/mcp`` (HTTP only)."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http" and _LEGACY_KEY_PATH.match(scope.get("path", "")):
            scope["path"] = "/mcp"
            scope["raw_path"] = b"/mcp"
        await self.app(scope, receive, send)
