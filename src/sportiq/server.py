"""FastMCP entry point. The uvx target is `main()`.

Per CLAUDE.md hard rule: this file MUST expose a `main()` function that calls
`mcp.run()`. `pyproject.toml` wires `[project.scripts] sportiq-mcp = "sportiq.server:main"`.

MCP servers on stdio are inherently single-client; 20 concurrent calls is a safe
ceiling against malformed client bursts without affecting normal single-client usage.
"""

import asyncio
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from sportiq.core.health import register_health_tool
from sportiq.core.instructions import register_instructions_resource
from sportiq.core.logging import configure_logging
from sportiq.core.param_docs import apply_param_descriptions
from sportiq.core.prompts import register_prompts
from sportiq.core.tool_telemetry import instrument_tools
from sportiq.cricket.tools import register_cricket_tools
from sportiq.f1.tools import register_f1_tools
from sportiq.football.tools import register_football_tools
from sportiq.server_tools.cross_sport import register_cross_sport_tools

# Infrastructure guard — not wired into tools yet; available when fan-out is added.
_SERVER_SEMAPHORE = asyncio.Semaphore(20)

configure_logging()

mcp = FastMCP("sportiq")

register_health_tool(mcp)
register_instructions_resource(mcp)
register_prompts(mcp)
# Registration order is the order of relevance (football → F1 → cricket); it
# determines how tools are listed to MCP clients. Imports above stay alphabetical
# (ruff isort); only these calls carry the relevance order.
register_football_tools(mcp)
register_f1_tools(mcp)
register_cricket_tools(mcp)
register_cross_sport_tools(mcp)
# After ALL registrations: surface docstring Args descriptions in tool schemas
# (FastMCP only schemas type hints; clients/directories score param descriptions).
apply_param_descriptions(mcp)
# Wrap each tool to emit a per-call `tool_call` telemetry event (success,
# latency, error code, calling client). Must run after every register_* call so
# the whole registry is wrapped; order vs apply_param_descriptions is irrelevant
# (that one only edits schemas, this one only swaps fn).
instrument_tools(mcp)


def main() -> None:
    """Entry point. Defaults to stdio (the uvx contract); serves streamable-HTTP
    when ``SPORTIQ_TRANSPORT=http`` (used by the remote/container deployment).

    On a remote host, set ``SPORTIQ_TRANSPORT=http``; the port is read from ``PORT``
    (Cloud Run / Fly / Render convention, default 8080) and bound on all interfaces.
    The MCP endpoint is served at ``/mcp``.
    """
    if os.getenv("SPORTIQ_TRANSPORT", "stdio").lower() in ("http", "streamable-http"):
        import uvicorn

        from sportiq.core.client_info import ClientInfoMiddleware
        from sportiq.core.pro_middleware import ProKeyMiddleware

        mcp.settings.host = "0.0.0.0"  # nosec B104  # container must bind all interfaces
        mcp.settings.port = int(os.getenv("PORT", "8080"))
        # DNS rebinding protection blocks Cloud Run host headers; disable it for
        # the remote deployment — Cloud Run's infrastructure handles perimeter security.
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )
        # Build the Starlette app ourselves so we can attach client-identification
        # logging (HTTP transport only), then run uvicorn directly. We do NOT call
        # mcp.run("streamable-http") here — it rebuilds the app and would drop the
        # middleware. Host/port/security settings above are read by the app build.
        app = mcp.streamable_http_app()
        app.add_middleware(ClientInfoMiddleware)
        # Added after ClientInfoMiddleware → outermost → runs first, so it can
        # rewrite a `/u/<key>/mcp` path to `/mcp` (and bind the per-request key)
        # before any downstream middleware/routing sees the request. Pure ASGI.
        app.add_middleware(ProKeyMiddleware)
        uvicorn.run(
            app,
            host=mcp.settings.host,
            port=mcp.settings.port,
            log_level=mcp.settings.log_level.lower(),
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
