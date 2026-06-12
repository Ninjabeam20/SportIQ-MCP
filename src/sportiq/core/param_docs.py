"""Inject docstring ``Args:`` descriptions into tool input schemas.

FastMCP builds each tool's ``inputSchema`` from type hints only — the per-param
descriptions in our (mandatory) docstring ``Args:`` blocks never reach the
schema, so MCP clients and directory scorers (e.g. Smithery "Parameter
descriptions") see undescribed parameters. This walks every registered tool
once at startup and copies each Args entry into the matching schema property.

Docstrings stay the single source of truth; tool signatures stay untouched.
"""
from __future__ import annotations

import re

_ARGS_BLOCK = re.compile(r"Args:\n(.*?)(?:\n\s*\n|\n\s*Returns:|\Z)", re.S)
_ARG_LINE = re.compile(r"\s{4,8}(\w+):\s*(.*)")


def _args_descriptions(doc: str | None) -> dict[str, str]:
    """Parse a Google-style docstring Args block into {param: description}."""
    match = _ARGS_BLOCK.search(doc or "")
    if not match:
        return {}
    out: dict[str, str] = {}
    current: str | None = None
    for line in match.group(1).splitlines():
        arg = _ARG_LINE.match(line)
        if arg:
            current = arg.group(1)
            out[current] = arg.group(2).strip()
        elif current and line.strip():  # continuation line of the same arg
            out[current] += " " + line.strip()
    return out


def apply_param_descriptions(mcp) -> None:
    """Copy docstring Args descriptions into every registered tool's schema."""
    tools = getattr(getattr(mcp, "_tool_manager", None), "_tools", None)
    if not tools:  # private FastMCP internals moved — degrade to no descriptions
        return
    for tool in tools.values():
        descs = _args_descriptions(getattr(tool.fn, "__doc__", None))
        properties = (tool.parameters or {}).get("properties", {})
        for name, prop in properties.items():
            if name in descs and "description" not in prop:
                prop["description"] = descs[name]
