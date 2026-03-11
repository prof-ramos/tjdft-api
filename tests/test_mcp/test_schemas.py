"""Tests for MCP schemas."""

import pytest

from app.mcp.schemas import SearchFilters, SearchToolInput

pytestmark = pytest.mark.unit


def test_search_filters_blank_values_are_normalized():
    filters = SearchFilters(relator="  ", classe="APC")

    assert filters.relator is None
    assert filters.classe == "APC"
    assert filters.to_client_kwargs() == {"classe": "APC"}


def test_search_tool_input_converts_page_to_upstream_contract():
    params = SearchToolInput(query=" tributario ", page=2, page_size=10)

    payload = params.to_client_kwargs()

    assert payload["query"] == "tributario"
    assert payload["pagina"] == 1
    assert payload["tamanho"] == 10
