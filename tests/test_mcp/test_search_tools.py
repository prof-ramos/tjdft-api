"""Tests for MCP search tools."""

from contextlib import asynccontextmanager

import pytest

import app.mcp.tools.search_tools as search_tools
from app.config import Settings
from app.mcp.schemas import MetadataToolInput, SearchAllPagesToolInput, SearchToolInput

pytestmark = pytest.mark.unit


class DummyClient:
    def __init__(self):
        self.received: dict[str, object] = {}

    async def buscar_simples(self, query: str, pagina: int, tamanho: int):
        self.received = {"query": query, "pagina": pagina, "tamanho": tamanho}
        return {"registros": [{"uuid": "1"}], "total": 1}

    async def buscar_com_filtros(self, **kwargs):
        self.received = kwargs
        return {"registros": [{"uuid": "2"}], "total": 1}

    async def buscar_todas_paginas(self, **kwargs):
        self.received = kwargs
        return [{"uuid": "a"}, {"uuid": "b"}]

    async def get_metadata(self):
        return {"classes": ["APC"], "relatores": ["RELATOR X"]}


class DummyRuntime:
    def __init__(self, client: DummyClient):
        self.settings = Settings(mcp_character_limit=5000)
        self._client = client

    @asynccontextmanager
    async def tjdft_client(self):
        yield self._client


@pytest.mark.asyncio
async def test_run_search_decisions_converts_page_to_zero_index(monkeypatch):
    monkeypatch.setattr(search_tools, "validate_relator", lambda _: True)
    monkeypatch.setattr(search_tools, "validate_classe", lambda _: True)
    monkeypatch.setattr(search_tools, "validate_orgao", lambda _: True)

    client = DummyClient()
    runtime = DummyRuntime(client)
    params = SearchToolInput(
        query="tributario",
        page=2,
        page_size=10,
        response_format="json",
    )

    rendered = await search_tools.run_search_decisions(params, runtime)

    assert '"total": 1' in rendered
    assert client.received["pagina"] == 1
    assert client.received["tamanho"] == 10


@pytest.mark.asyncio
async def test_run_get_metadata_returns_json():
    client = DummyClient()
    runtime = DummyRuntime(client)
    params = MetadataToolInput(response_format="json")

    rendered = await search_tools.run_get_metadata(params, runtime)

    assert '"classes"' in rendered
    assert '"APC"' in rendered


@pytest.mark.asyncio
async def test_run_search_all_pages_returns_pages_fetched(monkeypatch):
    monkeypatch.setattr(search_tools, "validate_relator", lambda _: True)
    monkeypatch.setattr(search_tools, "validate_classe", lambda _: True)
    monkeypatch.setattr(search_tools, "validate_orgao", lambda _: True)

    client = DummyClient()
    runtime = DummyRuntime(client)
    params = SearchAllPagesToolInput(
        query="",
        max_pages=3,
        page_size=1,
        response_format="json",
    )

    rendered = await search_tools.run_search_all_pages(params, runtime)

    assert '"pages_fetched": 2' in rendered
