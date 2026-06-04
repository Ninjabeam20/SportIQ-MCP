"""Registers sportiq://instructions as a FastMCP resource.

Any AI client can read this resource at session start to understand all 44 tools,
minimum-call recipes, envelope format, and staleness handling — reducing trial-and-error
calls significantly.
"""

from __future__ import annotations

from importlib.resources import files

from mcp.server.fastmcp import FastMCP

_INSTRUCTIONS_PATH = files("sportiq").joinpath("instructions.md")


def _load() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


def register_instructions_resource(mcp: FastMCP) -> None:
    @mcp.resource(
        "sportiq://instructions",
        name="sportiq-instructions",
        title="SportIQ AI Operating Guide",
        description=(
            "Read once at session start: tool catalogue, min-call recipes, "
            "envelope format, staleness rules, and error recovery for all 44 tools."
        ),
        mime_type="text/markdown",
    )
    def get_instructions() -> str:
        """Return the SportIQ AI operating guide."""
        return _load()
