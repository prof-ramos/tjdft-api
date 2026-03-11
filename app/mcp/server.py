"""Servidor MCP principal da aplicação."""

from mcp.server.fastmcp import FastMCP

from app.mcp.runtime import create_runtime
from app.mcp.tools import register_history_tools, register_search_tools

runtime = create_runtime()


def create_mcp_server() -> FastMCP:
    """Cria a instância do servidor MCP e registra as tools core."""
    server = FastMCP("TJDFT API")
    register_search_tools(server, runtime)
    register_history_tools(server, runtime)
    return server


mcp: FastMCP = create_mcp_server()
