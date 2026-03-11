"""Tools MCP core para busca e metadados do TJDFT."""

from __future__ import annotations

import math

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.mcp.constants import ResponseFormat
from app.mcp.errors import invalid_params, to_mcp_error
from app.mcp.formatters import format_response
from app.mcp.runtime import MCPRuntime
from app.mcp.schemas import (
    MetadataToolInput,
    SearchAllPagesToolInput,
    SearchFilters,
    SearchToolInput,
)
from app.utils.filtros import validate_classe, validate_orgao, validate_relator


def _coerce_response_format(value: ResponseFormat | str) -> ResponseFormat:
    if isinstance(value, ResponseFormat):
        return value
    try:
        return ResponseFormat(str(value))
    except ValueError as exc:
        raise invalid_params(
            "response_format inválido. Use 'markdown' ou 'json'.",
            data={"field": "response_format"},
        ) from exc


def _validate_filters(filters: SearchFilters | None) -> dict[str, str]:
    if filters is None:
        return {}

    normalized = filters.to_client_kwargs()
    errors: list[str] = []

    relator = normalized.get("relator")
    if relator and not validate_relator(relator):
        errors.append(f"relator inválido: {relator}")

    classe = normalized.get("classe")
    if classe and not validate_classe(classe):
        errors.append(f"classe inválida: {classe}")

    orgao = normalized.get("orgao_julgador")
    if orgao and not validate_orgao(orgao):
        errors.append(f"órgão julgador inválido: {orgao}")

    if errors:
        raise invalid_params(
            "; ".join(errors),
            data={"field": "filters", "invalid_filters": errors},
        )

    return normalized


async def run_search_decisions(params: SearchToolInput, runtime: MCPRuntime) -> str:
    filters = _validate_filters(params.filters)
    response_format = _coerce_response_format(params.response_format)

    async with runtime.tjdft_client() as client:
        if filters:
            result = await client.buscar_com_filtros(
                query=params.query,
                pagina=params.page - 1,
                tamanho=params.page_size,
                **filters,
            )
        else:
            result = await client.buscar_simples(
                query=params.query,
                pagina=params.page - 1,
                tamanho=params.page_size,
            )

    payload = {
        "items": result.get("registros", []),
        "total": int(result.get("total", 0)),
        "page": params.page,
        "page_size": params.page_size,
    }
    rendered, _ = format_response(
        payload,
        response_format=response_format,
        settings=runtime.settings,
        title="Resultados da busca TJDFT",
    )
    return rendered


async def run_get_metadata(params: MetadataToolInput, runtime: MCPRuntime) -> str:
    response_format = _coerce_response_format(params.response_format)

    async with runtime.tjdft_client() as client:
        metadata = await client.get_metadata()

    payload = {"data": metadata}
    rendered, _ = format_response(
        payload,
        response_format=response_format,
        settings=runtime.settings,
        title="Metadados disponíveis para filtros",
    )
    return rendered


async def run_search_all_pages(
    params: SearchAllPagesToolInput,
    runtime: MCPRuntime,
) -> str:
    filters = _validate_filters(params.filters)
    response_format = _coerce_response_format(params.response_format)

    async with runtime.tjdft_client() as client:
        items = await client.buscar_todas_paginas(
            query=params.query,
            max_paginas=params.max_pages,
            tamanho=params.page_size,
            **filters,
        )

    total = len(items)
    pages_fetched = (
        0 if total == 0 else min(params.max_pages, math.ceil(total / params.page_size))
    )
    payload = {
        "items": items,
        "total": total,
        "pages_fetched": pages_fetched,
        "page_size": params.page_size,
    }
    rendered, _ = format_response(
        payload,
        response_format=response_format,
        settings=runtime.settings,
        title="Busca agregada em múltiplas páginas",
    )
    return rendered


def register_search_tools(mcp: FastMCP, runtime: MCPRuntime) -> None:
    @mcp.tool(
        name="tjdft_search_decisions",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def tjdft_search_decisions(params: SearchToolInput) -> str:
        """Busca decisões do TJDFT com paginação 1-indexed e filtros oficiais."""
        try:
            return await run_search_decisions(params, runtime)
        except Exception as exc:
            raise to_mcp_error(exc) from exc

    @mcp.tool(
        name="tjdft_get_metadata",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def tjdft_get_metadata(params: MetadataToolInput) -> str:
        """Retorna metadados do TJDFT para montagem de filtros."""
        try:
            return await run_get_metadata(params, runtime)
        except Exception as exc:
            raise to_mcp_error(exc) from exc

    @mcp.tool(
        name="tjdft_search_all_pages",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def tjdft_search_all_pages(params: SearchAllPagesToolInput) -> str:
        """Agrega resultados de múltiplas páginas de busca, sem persistência local."""
        try:
            return await run_search_all_pages(params, runtime)
        except Exception as exc:
            raise to_mcp_error(exc) from exc
