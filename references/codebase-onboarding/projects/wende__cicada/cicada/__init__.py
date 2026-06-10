"""Cicada - An Elixir module search MCP server."""

from importlib.metadata import PackageNotFoundError, version


def _get_version() -> str:
    try:
        return version("cicada-mcp")
    except PackageNotFoundError:
        return "unknown"


__version__ = _get_version()
