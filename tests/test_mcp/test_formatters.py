"""Tests for MCP formatters."""

import pytest

from app.config import Settings
from app.mcp.constants import ResponseFormat
from app.mcp.formatters import format_response, truncate_text

pytestmark = pytest.mark.unit


def test_truncate_text_adds_actionable_message():
    settings = Settings(mcp_character_limit=1000)
    text = "x" * 2000

    truncated, info = truncate_text(text, settings=settings)

    assert len(truncated) <= 1000
    assert info is not None
    assert "Resposta truncada" in truncated


def test_format_response_json_keeps_structure_when_not_truncated():
    settings = Settings(mcp_character_limit=2000)
    payload = {"items": [{"id": 1}], "total": 1}

    rendered, info = format_response(
        payload,
        response_format=ResponseFormat.JSON,
        settings=settings,
    )

    assert '"total": 1' in rendered
    assert info is None
