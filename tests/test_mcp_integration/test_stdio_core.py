"""Core MCP stdio integration tests."""

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.timeout(30)
async def test_mcp_server_lists_core_tools(
    mcp_server_params: StdioServerParameters,
) -> None:
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()

    tool_names = {tool.name for tool in result.tools}
    assert "tjdft_search_decisions" in tool_names
    assert "tjdft_get_metadata" in tool_names
    assert "tjdft_search_all_pages" in tool_names
    assert "tjdft_get_consulta" in tool_names
    assert "tjdft_list_history" in tool_names
    assert "tjdft_find_similar_decisions" in tool_names
