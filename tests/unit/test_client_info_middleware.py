"""ClientInfoMiddleware must be a transparent pass-through for the MCP
streamable-HTTP transport.

Regression for the 2026-06-12 canary failure: the original BaseHTTPMiddleware
implementation consumed the request body (downstream handler saw it empty) and
broke the SSE response — initialize returned HTTP 200 with no payload. This
exercises the real app + middleware in-process (no network).
"""
from __future__ import annotations

from starlette.testclient import TestClient

from sportiq.core.client_info import ClientInfoMiddleware, _extract_client_info

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
    import json

    assert _extract_client_info(json.dumps(_INIT).encode()) == {
        "name": "middleware-e2e",
        "version": "1.0",
    }
    assert _extract_client_info(b'{"method":"tools/list"}') is None
    assert _extract_client_info(b"not json") is None
    assert _extract_client_info(b"") is None
