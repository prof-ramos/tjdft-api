"""Tools MCP core para histórico e consultas locais."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.mcp.constants import ResponseFormat
from app.mcp.errors import not_found, to_mcp_error
from app.mcp.formatters import format_response
from app.mcp.runtime import MCPRuntime
from app.mcp.schemas import (
    FindSimilarToolInput,
    GetConsultaToolInput,
    ListHistoryToolInput,
)
from app.repositories.decisao_repo import DecisaoRepository
from app.services.busca_service import BuscaService


def _coerce_response_format(value: ResponseFormat | str) -> ResponseFormat:
    if isinstance(value, ResponseFormat):
        return value
    return ResponseFormat(str(value))


async def run_get_consulta(params: GetConsultaToolInput, runtime: MCPRuntime) -> str:
    response_format = _coerce_response_format(params.response_format)

    async with runtime.session() as session:
        service = BuscaService(session=session, cache_manager=runtime.cache)
        data = await service.recuperar_busca(str(params.consulta_id))

    if data is None:
        raise not_found(
            f"Consulta não encontrada para o id informado: {params.consulta_id}"
        )

    payload = {"data": data}
    rendered, _ = format_response(
        payload,
        response_format=response_format,
        settings=runtime.settings,
        title="Consulta recuperada",
    )
    return rendered


async def run_list_history(params: ListHistoryToolInput, runtime: MCPRuntime) -> str:
    response_format = _coerce_response_format(params.response_format)

    async with runtime.session() as session:
        service = BuscaService(session=session, cache_manager=runtime.cache)
        items = await service.historico_consultas(
            usuario_id=str(params.usuario_id) if params.usuario_id else None,
            limite=params.limit,
        )

    payload = {
        "items": items,
        "total": len(items),
        "page": 1,
        "page_size": params.limit,
    }
    rendered, _ = format_response(
        payload,
        response_format=response_format,
        settings=runtime.settings,
        title="Histórico de consultas",
    )
    return rendered


async def run_find_similar(params: FindSimilarToolInput, runtime: MCPRuntime) -> str:
    response_format = _coerce_response_format(params.response_format)

    async with runtime.session() as session:
        repository = DecisaoRepository(session)
        reference = await repository.get_by_uuid(params.uuid_tjdft)
        if reference is None:
            raise not_found(
                f"Decisão de referência não encontrada no cache local: {params.uuid_tjdft}"
            )

        service = BuscaService(session=session, cache_manager=runtime.cache)
        items = await service.buscar_similares(
            uuid_tjdft=params.uuid_tjdft,
            limite=params.limit,
        )

    payload = {
        "items": items,
        "total": len(items),
        "page": 1,
        "page_size": params.limit,
    }
    rendered, _ = format_response(
        payload,
        response_format=response_format,
        settings=runtime.settings,
        title="Decisões similares",
    )
    return rendered


def register_history_tools(mcp: FastMCP, runtime: MCPRuntime) -> None:
    @mcp.tool(
        name="tjdft_get_consulta",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def tjdft_get_consulta(params: GetConsultaToolInput) -> str:
        """Recupera uma consulta persistida por `consulta_id`."""
        try:
            return await run_get_consulta(params, runtime)
        except Exception as exc:
            raise to_mcp_error(exc) from exc

    @mcp.tool(
        name="tjdft_list_history",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def tjdft_list_history(params: ListHistoryToolInput) -> str:
        """Lista histórico de consultas persistidas no banco local."""
        try:
            return await run_list_history(params, runtime)
        except Exception as exc:
            raise to_mcp_error(exc) from exc

    @mcp.tool(
        name="tjdft_find_similar_decisions",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def tjdft_find_similar_decisions(params: FindSimilarToolInput) -> str:
        """Busca decisões similares no cache local a partir de um UUID TJDFT."""
        try:
            return await run_find_similar(params, runtime)
        except Exception as exc:
            raise to_mcp_error(exc) from exc
