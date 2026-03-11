"""Registro de tools MCP por domínio funcional."""

from app.mcp.tools.ai_tools import register_ai_tools
from app.mcp.tools.history_tools import register_history_tools
from app.mcp.tools.search_tools import register_search_tools

__all__ = [
    "register_ai_tools",
    "register_history_tools",
    "register_search_tools",
]
