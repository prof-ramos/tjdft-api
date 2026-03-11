from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from app.mcp.runtime import create_runtime
from app.mcp.tools import (
    register_ai_tools,
    register_history_tools,
    register_search_tools,
)

runtime = create_runtime()


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Gerencia o ciclo de vida do servidor MCP."""
    await runtime.initialize()
    try:
        yield
    finally:
        await runtime.close()


def create_mcp_server() -> FastMCP:
    """Cria a instância do servidor MCP e registra as ferramentas."""
    server = FastMCP("TJDFT API", lifespan=app_lifespan)
    register_search_tools(server, runtime)
    register_history_tools(server, runtime)
    register_ai_tools(server, runtime)
    return server


mcp: FastMCP = create_mcp_server()
