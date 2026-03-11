"""Tools MCP para análise jurídica via IA usando o AIService."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.mcp.constants import ResponseFormat
from app.mcp.errors import to_mcp_error
from app.mcp.formatters import format_response
from app.mcp.runtime import MCPRuntime
from app.mcp.schemas import (
    CompareDecisionsToolInput,
    ExtractThesesToolInput,
    SummarizeEmentaToolInput,
)

logger = logging.getLogger(__name__)


def _coerce_response_format(value: ResponseFormat | str) -> ResponseFormat:
    """Coage um formato de resposta para o enum ResponseFormat.

    Args:
        value: O formato de resposta como enum ou string.

    Returns:
        O formato de resposta como ResponseFormat.

    Raises:
        ValueError: Se o valor não for um ResponseFormat válido.
    """
    if isinstance(value, ResponseFormat):
        return value
    try:
        return ResponseFormat(value)
    except ValueError as exc:
        raise ValueError(
            f"Formato de resposta inválido: '{value}'. "
            f"Valores válidos: {[f.value for f in ResponseFormat]}"
        ) from exc


async def run_ai_summarize(
    params: SummarizeEmentaToolInput, runtime: MCPRuntime
) -> str:
    """Gera um resumo analítico de uma ementa judicial usando o serviço de IA.

    Args:
        params: Parâmetros de entrada contendo a ementa e tokens máximos.
        runtime: O runtime do MCP para acesso a serviços e configurações.

    Returns:
        O resumo formatado conforme o response_format solicitado ou mensagem de erro.
    """
    response_format = _coerce_response_format(params.response_format)

    async with runtime.optional_ai_service() as ai_service:
        if ai_service is None:
            return "Serviço de IA não disponível ou desabilitado nas configurações."

        result = await ai_service.resumir_ementa(
            ementa=params.ementa,
            max_tokens=params.max_tokens,
        )

    if result is None:
        return "Não foi possível gerar o resumo da ementa."

    rendered, _ = format_response(
        result,
        response_format=response_format,
        settings=runtime.settings,
        title="Resumo Analítico da Ementa",
    )
    return rendered


async def run_ai_extract_theses(
    params: ExtractThesesToolInput,
    runtime: MCPRuntime,
) -> str:
    """Extrai teses jurídicas de uma decisão judicial usando o serviço de IA.

    Args:
        params: Parâmetros de entrada contendo a ementa ou inteiro teor.
        runtime: O runtime do MCP para acesso a serviços e configurações.

    Returns:
        As teses extraídas e formatadas ou mensagem de erro.
    """
    response_format = _coerce_response_format(params.response_format)

    async with runtime.optional_ai_service() as ai_service:
        if ai_service is None:
            return "Serviço de IA não disponível ou desabilitado nas configurações."

        result = await ai_service.extrair_teses(
            ementa=params.ementa,
            inteiro_teor=params.inteiro_teor,
        )

    if result is None:
        return "Não foi possível extrair as teses jurídicas."

    payload = {"teses": result}
    rendered, _ = format_response(
        payload,
        response_format=response_format,
        settings=runtime.settings,
        title="Teses Jurídicas Identificadas",
    )
    return rendered


async def run_ai_compare_decisions(
    params: CompareDecisionsToolInput,
    runtime: MCPRuntime,
) -> str:
    """Compara múltiplas decisões judiciais identificando convergências e divergências.

    Args:
        params: Parâmetros de entrada contendo a lista de ementas.
        runtime: O runtime do MCP para acesso a serviços e configurações.

    Returns:
        A análise comparativa formatada ou mensagem de erro.
    """
    response_format = _coerce_response_format(params.response_format)

    async with runtime.optional_ai_service() as ai_service:
        if ai_service is None:
            return "Serviço de IA não disponível ou desabilitado nas configurações."

        result = await ai_service.comparar_decisoes(ementas=params.ementas)

    if result is None:
        return "Não foi possível realizar a comparação entre as decisões."

    rendered, _ = format_response(
        result,
        response_format=response_format,
        settings=runtime.settings,
        title="Comparação Jurisprudencial",
    )
    return rendered


def register_ai_tools(mcp: FastMCP, runtime: MCPRuntime) -> None:
    """Registra as ferramentas de IA no servidor FastMCP.

    Args:
        mcp: A instância do servidor FastMCP.
        runtime: O runtime do MCP para injeção nas ferramentas.
    """

    @mcp.tool(
        name="tjdft_ai_summarize",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def tjdft_ai_summarize(params: SummarizeEmentaToolInput) -> str:
        """Gera resumo analítico e pontos-chave de uma ementa judicial via IA."""
        try:
            return await run_ai_summarize(params, runtime)
        except Exception as exc:
            logger.error(f"Erro em tjdft_ai_summarize: {exc}")
            raise to_mcp_error(exc) from exc

    @mcp.tool(
        name="tjdft_ai_extract_theses",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def tjdft_ai_extract_theses(params: ExtractThesesToolInput) -> str:
        """Extrai teses jurídicas (constitucional, etc.) de uma decisão via IA."""
        try:
            return await run_ai_extract_theses(params, runtime)
        except Exception as exc:
            logger.error(f"Erro em tjdft_ai_extract_theses: {exc}")
            raise to_mcp_error(exc) from exc

    @mcp.tool(
        name="tjdft_ai_compare_decisions",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def tjdft_ai_compare_decisions(params: CompareDecisionsToolInput) -> str:
        """Compara múltiplas decisões identificando divergências e convergências via IA."""
        try:
            return await run_ai_compare_decisions(params, runtime)
        except Exception as exc:
            logger.error(f"Erro em tjdft_ai_compare_decisions: {exc}")
            raise to_mcp_error(exc) from exc
