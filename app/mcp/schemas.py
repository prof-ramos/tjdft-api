"""Schemas Pydantic v2 compartilhados pela camada MCP."""

from __future__ import annotations

from typing import Annotated, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.mcp.constants import (
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_MAX_PAGES,
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SIMILAR_LIMIT,
    MAX_PAGE_SIZE,
    ResponseFormat,
)

ResponseItemT = TypeVar("ResponseItemT")


class MCPBaseModel(BaseModel):
    """Base comum para schemas MCP com validação estrita."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )


class SearchFilters(MCPBaseModel):
    """Filtros oficiais suportados pelo contrato MCP."""

    relator: str | None = Field(default=None, description="Nome do relator")
    classe: str | None = Field(default=None, description="Classe processual")
    orgao_julgador: str | None = Field(
        default=None,
        description="Órgão julgador",
    )
    base: str | None = Field(default=None, description="Base documental")
    subbase: str | None = Field(default=None, description="Subbase documental")
    processo: str | None = Field(default=None, description="Número do processo")
    revisor: str | None = Field(default=None, description="Nome do revisor")
    relator_designado: str | None = Field(
        default=None,
        description="Nome do relator designado",
    )

    @field_validator("*", mode="before")
    @classmethod
    def blank_strings_to_none(cls, value: object) -> object:
        """Normaliza strings vazias de filtros opcionais para None."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def to_client_kwargs(self) -> dict[str, str]:
        """Retorna apenas filtros preenchidos, prontos para o client."""
        data = self.model_dump(exclude_none=True)
        return {key: str(value) for key, value in data.items()}

    @property
    def is_empty(self) -> bool:
        """Indica se não há filtros válidos preenchidos."""
        return not bool(self.model_dump(exclude_none=True))


class ResponseFormatMixin(MCPBaseModel):
    """Mixin para tools que aceitam retorno em markdown ou json."""

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato de resposta retornado pela tool",
    )


class SearchToolInput(ResponseFormatMixin):
    """Entrada para a tool core de busca paginada."""

    query: str = Field(
        default="",
        description="Consulta textual; string vazia remove o filtro textual",
    )
    filters: SearchFilters | None = Field(
        default=None,
        description="Filtros estruturados oficiais do contrato MCP",
    )
    page: int = Field(
        default=DEFAULT_PAGE,
        ge=1,
        description="Página 1-indexed exposta pelo MCP",
    )
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Quantidade de itens por página (1..40)",
    )

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value: object) -> object:
        """Converte entradas compostas só por espaços em string vazia."""
        if isinstance(value, str):
            return value.strip()
        return value

    def to_client_kwargs(self) -> dict[str, str | int]:
        """Converte a entrada para o contrato interno do client TJDFT."""
        payload: dict[str, str | int] = {
            "query": self.query,
            "pagina": self.page - 1,
            "tamanho": self.page_size,
        }
        if self.filters is not None and not self.filters.is_empty:
            payload.update(self.filters.to_client_kwargs())
        return payload


class MetadataToolInput(ResponseFormatMixin):
    """Entrada para a tool de metadados."""


class SearchAllPagesToolInput(ResponseFormatMixin):
    """Entrada para a tool que agrega múltiplas páginas."""

    query: str = Field(
        default="",
        description="Consulta textual; string vazia remove o filtro textual",
    )
    filters: SearchFilters | None = Field(
        default=None,
        description="Filtros estruturados oficiais do contrato MCP",
    )
    max_pages: int = Field(
        default=DEFAULT_MAX_PAGES,
        ge=1,
        description="Número máximo de páginas a coletar",
    )
    page_size: int = Field(
        default=MAX_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Quantidade de itens por página em cada chamada upstream",
    )

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value: object) -> object:
        """Converte entradas compostas só por espaços em string vazia."""
        if isinstance(value, str):
            return value.strip()
        return value

    def to_client_kwargs(self) -> dict[str, str | int]:
        """Converte a entrada para o contrato do client TJDFT."""
        payload: dict[str, str | int] = {
            "query": self.query,
            "max_paginas": self.max_pages,
            "tamanho": self.page_size,
        }
        if self.filters is not None and not self.filters.is_empty:
            payload.update(self.filters.to_client_kwargs())
        return payload


class GetConsultaToolInput(ResponseFormatMixin):
    """Entrada para recuperar uma consulta já persistida."""

    consulta_id: UUID = Field(description="UUID da consulta persistida")


class ListHistoryToolInput(ResponseFormatMixin):
    """Entrada para listar histórico de consultas já persistidas."""

    usuario_id: UUID | None = Field(
        default=None,
        description="UUID do usuário; omitido para histórico geral",
    )
    limit: int = Field(
        default=DEFAULT_HISTORY_LIMIT,
        ge=1,
        description="Quantidade máxima de consultas retornadas",
    )


class FindSimilarToolInput(ResponseFormatMixin):
    """Entrada para buscar decisões similares no cache local."""

    uuid_tjdft: str = Field(
        min_length=1,
        description="UUID TJDFT da decisão de referência",
    )
    limit: int = Field(
        default=DEFAULT_SIMILAR_LIMIT,
        ge=1,
        description="Quantidade máxima de decisões similares retornadas",
    )


class TruncationInfo(MCPBaseModel):
    """Metadados sobre truncamento aplicado a uma resposta."""

    limit: int = Field(ge=1, description="Limite de caracteres utilizado")
    original_length: int = Field(
        ge=0,
        description="Quantidade de caracteres antes do truncamento",
    )
    returned_length: int = Field(
        ge=0,
        description="Quantidade de caracteres retornados após truncamento",
    )
    message: str = Field(description="Mensagem acionável explicando o truncamento")
    hints: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Sugestões para obter uma resposta mais útil",
    )


class ListResponseEnvelope(MCPBaseModel, Generic[ResponseItemT]):
    """Envelope padronizado para tools MCP que retornam coleções."""

    items: list[ResponseItemT] = Field(default_factory=list)
    total: int = Field(ge=0, description="Total de itens disponíveis")
    page: int | None = Field(
        default=None,
        ge=1,
        description="Página atual quando houver paginação",
    )
    page_size: int | None = Field(
        default=None,
        ge=1,
        description="Tamanho da página quando houver paginação",
    )
    pages_fetched: int | None = Field(
        default=None,
        ge=0,
        description="Quantidade de páginas agregadas, quando aplicável",
    )
    truncated: TruncationInfo | None = Field(
        default=None,
        description="Metadados de truncamento aplicado à renderização",
    )


class ObjectResponseEnvelope(MCPBaseModel, Generic[ResponseItemT]):
    """Envelope padronizado para tools MCP que retornam um único objeto."""

    data: ResponseItemT
    truncated: TruncationInfo | None = Field(
        default=None,
        description="Metadados de truncamento aplicado à renderização",
    )


class AIContextMixin(MCPBaseModel):
    """Mixin para ferramentas de IA que aceitam contexto adicional."""

    contexto: str | None = Field(
        default=None,
        description="Contexto extra (fatos do caso, petição, etc.) para orientar a IA",
    )


class SummarizeEmentaToolInput(ResponseFormatMixin, AIContextMixin):
    """Entrada para a tool de resumo de ementa."""

    ementa: str = Field(min_length=10, description="Texto da ementa judicial a resumir")
    max_tokens: int = Field(
        default=300,
        ge=50,
        le=1000,
        description="Limite de tokens para o resumo gerado",
    )


class ExtractThesesToolInput(ResponseFormatMixin, AIContextMixin):
    """Entrada para a tool de extração de teses."""

    ementa: str = Field(min_length=10, description="Texto da ementa judicial")
    inteiro_teor: str | None = Field(
        default=None,
        description="Texto completo do inteiro teor para análise profunda",
    )


class CompareDecisionsToolInput(ResponseFormatMixin, AIContextMixin):
    """Entrada para a tool de comparação de decisões."""

    ementas: list[Annotated[str, Field(min_length=10)]] = Field(
        min_length=2,
        max_length=5,
        description="Lista de ementas para comparar (mínimo 2, máximo 5)",
    )
