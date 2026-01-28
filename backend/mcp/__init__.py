"""
MCP Tools Package for Planalytics AI
=====================================

This package exposes Planalytics agent functionality via the Model Context Protocol (MCP).

Components:
- tools.py: 13 MCP tool definitions (Developer A)
- schemas.py: JSON schemas for tool parameters (Developer A)
- server.py: MCP server implementation (Developer B)
- config.json: Claude Desktop configuration (Developer B)

Usage:
    from mcp.tools import mcp_server, TOOL_REGISTRY
"""

__version__ = "1.0.0"

# Import tools when MCP SDK is available
try:
    from .tools import mcp_server, TOOL_REGISTRY, list_tools, get_tool
    __all__ = ["mcp_server", "TOOL_REGISTRY", "list_tools", "get_tool"]
except ImportError as e:
    # MCP SDK not installed yet - graceful degradation
    import warnings
    warnings.warn(f"MCP SDK not installed: {e}. Tools will not be available until 'pip install mcp' is run.")
    __all__ = []
