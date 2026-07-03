"""LegacyKeyPathMiddleware must rewrite old ``/u/<key>/mcp`` connector URLs to
``/mcp`` and leave every other path untouched.

Regression for the 2026-07-01 free rollout: removing the entitlement gate also
removed the path rewrite, so sponsors' AI connectors (configured with the
``/u/<key>/mcp`` URL from the welcome message) started 404ing. Tested against a
recording ASGI app rather than the real FastMCP app — the streamable-HTTP
session manager can only be started once per process and
test_client_info_middleware already owns that slot.
"""
from __future__ import annotations

from sportiq.core.path_compat import LegacyKeyPathMiddleware


class _RecordingApp:
    """Minimal ASGI app that records the scope it was called with."""

    def __init__(self) -> None:
        self.scopes: list[dict] = []

    async def __call__(self, scope, receive, send) -> None:
        self.scopes.append(scope)


async def _run(path: str, scope_type: str = "http") -> dict:
    inner = _RecordingApp()
    mw = LegacyKeyPathMiddleware(inner)
    scope = {"type": scope_type, "path": path, "raw_path": path.encode()}
    await mw(scope, None, None)
    return inner.scopes[0]


async def test_legacy_key_path_rewritten_to_mcp():
    for path in ("/u/sq_somesharedkey/mcp", "/u/sq_somesharedkey/mcp/"):
        scope = await _run(path)
        assert scope["path"] == "/mcp"
        assert scope["raw_path"] == b"/mcp"


async def test_non_matching_paths_untouched():
    for path in ("/mcp", "/u/onlykey", "/u/key/extra/mcp", "/robots.txt"):
        scope = await _run(path)
        assert scope["path"] == path
        assert scope["raw_path"] == path.encode()


async def test_non_http_scope_passes_through():
    scope = await _run("/u/sq_key/mcp", scope_type="websocket")
    assert scope["path"] == "/u/sq_key/mcp"
