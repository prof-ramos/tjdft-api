"""Tests for MCP history tools."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from mcp.shared.exceptions import McpError

import app.mcp.tools.history_tools as history_tools
from app.config import Settings
from app.mcp.schemas import (
    FindSimilarToolInput,
    GetConsultaToolInput,
    ListHistoryToolInput,
)

pytestmark = pytest.mark.unit


class DummyRuntime:
    def __init__(self):
        self.settings = Settings(mcp_character_limit=5000)
        self.cache = SimpleNamespace()

    @asynccontextmanager
    async def session(self):
        yield SimpleNamespace()


@pytest.mark.asyncio
async def test_run_get_consulta_raises_not_found(monkeypatch):
    class DummyBuscaService:
        def __init__(self, session, cache_manager):
            self.session = session
            self.cache_manager = cache_manager

        async def recuperar_busca(self, consulta_id: str):
            return None

    monkeypatch.setattr(history_tools, "BuscaService", DummyBuscaService)

    runtime = DummyRuntime()
    params = GetConsultaToolInput(consulta_id=uuid4())

    with pytest.raises(McpError):
        await history_tools.run_get_consulta(params, runtime)


@pytest.mark.asyncio
async def test_run_list_history_returns_json(monkeypatch):
    class DummyBuscaService:
        def __init__(self, session, cache_manager):
            self.session = session
            self.cache_manager = cache_manager

        async def historico_consultas(self, usuario_id=None, limite=20):
            return [{"id": "1", "query": "tributario"}]

    monkeypatch.setattr(history_tools, "BuscaService", DummyBuscaService)

    runtime = DummyRuntime()
    params = ListHistoryToolInput(limit=5, response_format="json")

    rendered = await history_tools.run_list_history(params, runtime)

    assert '"total": 1' in rendered


@pytest.mark.asyncio
async def test_run_find_similar_requires_cached_reference(monkeypatch):
    class DummyRepository:
        def __init__(self, session):
            self.session = session

        async def get_by_uuid(self, uuid_tjdft: str):
            return None

    monkeypatch.setattr(history_tools, "DecisaoRepository", DummyRepository)

    runtime = DummyRuntime()
    params = FindSimilarToolInput(uuid_tjdft="missing-uuid", limit=5)

    with pytest.raises(McpError):
        await history_tools.run_find_similar(params, runtime)
