"""Testes unitários para ferramentas de IA do MCP."""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.mcp.constants import ResponseFormat
from app.mcp.schemas import (
    CompareDecisionsToolInput,
    ExtractThesesToolInput,
    SummarizeEmentaToolInput,
)
from app.mcp.tools.ai_tools import (
    run_ai_compare_decisions,
    run_ai_extract_theses,
    run_ai_summarize,
)


@asynccontextmanager
async def mock_ai_context(service: Any) -> AsyncIterator[Any]:
    """Helper para mockar o contexto assíncrono do serviço de IA.

    Args:
        service: O serviço a ser retornado pelo contexto.
    """
    yield service


@pytest.fixture
def mock_runtime() -> MagicMock:
    """Fixture que cria um runtime mockado com as configurações necessárias."""
    runtime = MagicMock()
    runtime.settings.mcp_character_limit = 1000
    runtime.settings.mcp_enable_ai_tools = True
    return runtime


@pytest.fixture
def mock_ai_service() -> AsyncMock:
    """Fixture que cria um serviço de IA mockado."""
    return AsyncMock()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response_format", [ResponseFormat.JSON, ResponseFormat.MARKDOWN]
)
async def test_run_ai_summarize_success(mock_runtime, mock_ai_service, response_format):
    mock_ai_service.resumir_ementa.return_value = {
        "resumo": "Decisão sobre imposto.",
        "pontos_chave": ["ponto 1"],
    }

    mock_runtime.optional_ai_service.return_value = mock_ai_context(mock_ai_service)

    params = SummarizeEmentaToolInput(
        ementa="Ementa longa de teste para resumo.", response_format=response_format
    )

    result = await run_ai_summarize(params, mock_runtime)
    assert "Decisão sobre imposto" in result
    assert "ponto 1" in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response_format", [ResponseFormat.JSON, ResponseFormat.MARKDOWN]
)
async def test_run_ai_extract_theses_success(
    mock_runtime, mock_ai_service, response_format
):
    mock_ai_service.extrair_teses.return_value = [
        {"tese": "Tese 1", "contexto": "Tribunal", "tipo": "Civil"}
    ]

    mock_runtime.optional_ai_service.return_value = mock_ai_context(mock_ai_service)

    params = ExtractThesesToolInput(
        ementa="Ementa para extração de teses.", response_format=response_format
    )

    result = await run_ai_extract_theses(params, mock_runtime)
    assert "Tese 1" in result
    assert "Civil" in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response_format", [ResponseFormat.JSON, ResponseFormat.MARKDOWN]
)
async def test_run_ai_compare_decisions_success(
    mock_runtime, mock_ai_service, response_format
):
    mock_ai_service.comparar_decisoes.return_value = {
        "similaridades": ["sim 1"],
        "diferencas": ["dif 1"],
        "posicao_majoritaria": "Aprovado",
    }

    mock_runtime.optional_ai_service.return_value = mock_ai_context(mock_ai_service)

    params = CompareDecisionsToolInput(
        ementas=[
            "Ementa de teste numero um para comparacao",
            "Ementa de teste numero dois para comparacao",
        ],
        response_format=response_format,
    )

    result = await run_ai_compare_decisions(params, mock_runtime)
    assert "sim 1" in result
    assert "Aprovado" in result


@pytest.mark.asyncio
async def test_run_ai_service_unavailable():
    runtime = MagicMock()
    runtime.settings.mcp_enable_ai_tools = False
    runtime.optional_ai_service.return_value = mock_ai_context(None)

    params = SummarizeEmentaToolInput(ementa="Ementa teste")
    result = await run_ai_summarize(params, runtime)

    assert "não disponível" in result.lower()
