"""Tests for ProKeyMiddleware (per-request Pro-key extraction, pure ASGI).

Drives the middleware with a recording downstream app and asserts the key the
gate would see (``get_active_key``) plus the rewritten request path. Verifies the
contextvar is reset after each request so keys never leak across requests.
"""
from __future__ import annotations

from sportiq.core.entitlements import get_active_key
from sportiq.core.pro_middleware import ProKeyMiddleware


def _scope(path: str = "/mcp", headers: list | None = None) -> dict:
    return {"type": "http", "method": "POST", "path": path, "headers": headers or []}


async def _run(scope: dict) -> dict:
    """Run the middleware over ``scope`` with a recording app; return what the
    downstream handler observed (active key + final path)."""
    captured: dict = {}

    async def app(scope, receive, send):
        captured["key"] = get_active_key()
        captured["path"] = scope["path"]

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        pass

    await ProKeyMiddleware(app)(scope, receive, send)
    return captured


async def test_header_bearer_binds_key():
    """Authorization: Bearer <key> → that key is active downstream."""
    cap = await _run(_scope(headers=[(b"authorization", b"Bearer sq_header")]))
    assert cap["key"] == "sq_header"


async def test_url_path_binds_key_and_rewrites_path():
    """/u/<key>/mcp → key active downstream AND path rewritten to /mcp."""
    cap = await _run(_scope(path="/u/sq_path/mcp"))
    assert cap["key"] == "sq_path"
    assert cap["path"] == "/mcp"


async def test_url_path_with_trailing_slash():
    """/u/<key>/mcp/ (trailing slash) still extracts and normalises to /mcp."""
    cap = await _run(_scope(path="/u/sq_path/mcp/"))
    assert cap["key"] == "sq_path"
    assert cap["path"] == "/mcp"


async def test_no_key_leaves_context_empty():
    """No path key and no header → nothing bound; path untouched."""
    cap = await _run(_scope())
    assert cap["key"] is None
    assert cap["path"] == "/mcp"


async def test_key_reset_after_request():
    """The per-request key is cleared once the request completes (no leak)."""
    await _run(_scope(headers=[(b"authorization", b"Bearer sq_header")]))
    assert get_active_key() is None  # contextvar reset; env key blanked by fixture


async def test_non_http_scope_passes_through():
    """A lifespan (non-http) scope is forwarded untouched, no key handling."""
    called: dict = {}

    async def app(scope, receive, send):
        called["ok"] = True

    await ProKeyMiddleware(app)({"type": "lifespan"}, None, None)
    assert called["ok"] is True
