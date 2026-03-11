"""Fixtures for MCP stdio integration tests."""

import os

import pytest
from mcp import StdioServerParameters


@pytest.fixture
def mcp_server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "app.mcp"],
        env=dict(os.environ),
    )
