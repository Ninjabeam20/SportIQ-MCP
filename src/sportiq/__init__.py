"""sportiq-mcp — MCP server for football, F1, and cricket intelligence tools."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sportiq-mcp")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0.dev0"
