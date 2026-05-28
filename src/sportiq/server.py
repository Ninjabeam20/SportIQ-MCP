"""FastMCP entry point. The uvx target is `main()`.

Per CLAUDE.md hard rule: this file MUST expose a `main()` function that calls
`mcp.run()`. `pyproject.toml` wires `[project.scripts] sportiq-mcp = "sportiq.server:main"`.
"""

from mcp.server.fastmcp import FastMCP

from sportiq.core.health import register_health_tool
from sportiq.core.logging import configure_logging
from sportiq.cricket.tools import register_cricket_tools
from sportiq.f1.tools import register_f1_tools

configure_logging()

mcp = FastMCP("sportiq")

register_health_tool(mcp)
register_cricket_tools(mcp)
register_f1_tools(mcp)


def main() -> None:
    """uvx entry point. Runs the MCP server on stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
