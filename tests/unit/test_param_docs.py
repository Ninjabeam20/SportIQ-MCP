"""Every registered tool parameter must carry a schema description (injected
from the docstring Args block by core/param_docs.py at server import)."""
from __future__ import annotations

from sportiq.core.param_docs import _args_descriptions


def test_every_tool_param_has_schema_description():
    from sportiq.server import mcp

    undescribed = []
    for name, tool in mcp._tool_manager._tools.items():
        for param, prop in (tool.parameters or {}).get("properties", {}).items():
            if not prop.get("description"):
                undescribed.append(f"{name}.{param}")
    assert not undescribed, f"params missing schema descriptions: {undescribed}"


def test_args_parser_handles_continuation_lines():
    doc = """Do a thing.

    Args:
        alpha: First line
            continued on the next line.
        beta: Single line.

    Returns:
        Nothing relevant.
    """
    descs = _args_descriptions(doc)
    assert descs["alpha"] == "First line continued on the next line."
    assert descs["beta"] == "Single line."


def test_args_parser_no_args_block():
    assert _args_descriptions("Just a summary.") == {}
    assert _args_descriptions(None) == {}
