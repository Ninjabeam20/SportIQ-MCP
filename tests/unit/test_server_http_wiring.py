"""HTTP transport wiring: middleware order and bind settings.

Regression for the 'do not call mcp.run(\"streamable-http\")' invariant —
that rebuilds the Starlette app and drops middlewares. LegacyKeyPathMiddleware
must be outermost so /u/<key>/mcp rewrites before rate-limit and client-info.
"""

from __future__ import annotations

import uvicorn

from sportiq.core.client_info import ClientInfoMiddleware
from sportiq.core.request_limits import RequestLimitMiddleware


def test_http_middleware_order_and_bind(monkeypatch):
    captured: dict = {}

    def fake_run(app, **kwargs):
        captured["app"] = app
        captured["kwargs"] = kwargs

    monkeypatch.setenv("SPORTIQ_TRANSPORT", "http")
    monkeypatch.setenv("PORT", "8099")
    monkeypatch.setattr(uvicorn, "run", fake_run)

    from sportiq.server import main

    main()

    assert "app" in captured
    names = [m.cls.__name__ for m in captured["app"].user_middleware]
    assert names[0] == "LegacyKeyPathMiddleware"
    assert RequestLimitMiddleware.__name__ in names
    assert ClientInfoMiddleware.__name__ in names
    assert names.index("LegacyKeyPathMiddleware") < names.index("RequestLimitMiddleware")
    assert names.index("LegacyKeyPathMiddleware") < names.index("ClientInfoMiddleware")
    assert captured["kwargs"]["host"] == "0.0.0.0"
    assert captured["kwargs"]["port"] == 8099


def test_http_transport_is_stateless(monkeypatch):
    """HTTP mode must build a stateless app: no per-connector session to strand.

    A `compose up --build` on the home server restarts the container; with
    sessions, every live connector holds a dead Mcp-Session-Id until the user
    removes and re-adds it. Stateless means each POST stands alone.
    `json_response` stays False — SSE framing is what streams tool results.
    """
    monkeypatch.setenv("SPORTIQ_TRANSPORT", "http")
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: None)

    from sportiq.server import main, mcp

    main()

    assert mcp.settings.stateless_http is True
    assert mcp.settings.json_response is False


def test_stdio_transport_does_not_force_stateless(monkeypatch):
    """stdio is the uvx contract and never touches the HTTP settings."""
    monkeypatch.setenv("SPORTIQ_TRANSPORT", "stdio")
    ran: dict = {}

    from sportiq.server import main, mcp

    monkeypatch.setattr(mcp, "run", lambda *a, **k: ran.setdefault("stdio", True))
    monkeypatch.setattr(mcp.settings, "stateless_http", False)

    main()

    assert ran.get("stdio") is True
    assert mcp.settings.stateless_http is False


def test_mcp_serverinfo_version_matches_package():
    from sportiq import __version__
    from sportiq.server import mcp

    assert mcp._mcp_server.version == __version__
