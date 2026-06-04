"""FastMCP entry point. The uvx target is `main()`.

Per CLAUDE.md hard rule: this file MUST expose a `main()` function that calls
`mcp.run()`. `pyproject.toml` wires `[project.scripts] sportiq-mcp = "sportiq.server:main"`.

MCP servers on stdio are inherently single-client; 20 concurrent calls is a safe
ceiling against malformed client bursts without affecting normal single-client usage.
"""

import asyncio

from mcp.server.fastmcp import FastMCP

from sportiq.core.health import register_health_tool
from sportiq.core.instructions import register_instructions_resource
from sportiq.core.logging import configure_logging
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
register_cricket_tools(mcp)
register_f1_tools(mcp)
register_football_tools(mcp)
register_cross_sport_tools(mcp)


def main() -> None:
    """uvx entry point. Runs the MCP server on stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
