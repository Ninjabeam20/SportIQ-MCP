"""Every tool's outputSchema must validate the envelope shapes FastMCP emits.

Regression guard for the "Output validation error: None is not of type 'object'"
break: FastMCP fills absent envelope keys with ``null`` in ``structuredContent``,
and the mcp lowlevel server validates that against the tool's ``outputSchema``
before sending. The rest of the suite calls tool functions directly and never
exercises this validation path, so it is asserted here for all 44 tools.

Two shapes must pass for every tool that declares an outputSchema:
  - success: ``{"data": {...}, "meta": {...}, "error": None}``
  - failure: ``{"data": None, "meta": None, "error": {...}}``
"""

from __future__ import annotations

import asyncio

import jsonschema
import pytest

from sportiq import server

_TOOLS = asyncio.run(server.mcp.list_tools())
_TOOLS_WITH_SCHEMA = [t for t in _TOOLS if getattr(t, "outputSchema", None) is not None]

_SUCCESS_ENVELOPE = {"data": {"x": 1}, "meta": {"source": "cricapi"}, "error": None}
_ERROR_ENVELOPE = {
    "data": None,
    "meta": None,
    "error": {"code": "ALL_SOURCES_FAILED", "message": "boom"},
}


def test_every_tool_declares_output_schema():
    """All registered tools return the Envelope, so all must carry an outputSchema."""
    missing = [t.name for t in _TOOLS if getattr(t, "outputSchema", None) is None]
    assert missing == [], f"tools without outputSchema: {missing}"


@pytest.mark.parametrize("tool", _TOOLS_WITH_SCHEMA, ids=lambda t: t.name)
def test_output_schema_validates_success_envelope(tool):
    """The success envelope FastMCP emits (error filled with null) must validate."""
    jsonschema.validate(instance=_SUCCESS_ENVELOPE, schema=tool.outputSchema)


@pytest.mark.parametrize("tool", _TOOLS_WITH_SCHEMA, ids=lambda t: t.name)
def test_output_schema_validates_error_envelope(tool):
    """The error envelope FastMCP emits (data/meta filled with null) must validate."""
    jsonschema.validate(instance=_ERROR_ENVELOPE, schema=tool.outputSchema)
