"""Constantes e tipos compartilhados pela camada MCP."""

from __future__ import annotations

from enum import Enum
from typing import Final, TypeAlias


class ResponseFormat(str, Enum):
    """Formatos de resposta suportados pelas tools MCP."""

    MARKDOWN = "markdown"
    JSON = "json"


JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]

SUPPORTED_FILTER_KEYS: Final[tuple[str, ...]] = (
    "relator",
    "classe",
    "orgao_julgador",
    "base",
    "subbase",
    "processo",
    "revisor",
    "relator_designado",
)

VALIDATED_FILTER_KEYS: Final[tuple[str, ...]] = (
    "relator",
    "classe",
    "orgao_julgador",
)

PASSTHROUGH_FILTER_KEYS: Final[tuple[str, ...]] = (
    "base",
    "subbase",
    "processo",
    "revisor",
    "relator_designado",
)

DEFAULT_PAGE: Final[int] = 1
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 40
DEFAULT_MAX_PAGES: Final[int] = 3
DEFAULT_HISTORY_LIMIT: Final[int] = 20
DEFAULT_SIMILAR_LIMIT: Final[int] = 10

DEFAULT_TRUNCATION_HINTS: Final[tuple[str, ...]] = (
    "reduza page_size, max_pages ou limit",
    "refine os filtros para retornar menos itens",
    "use response_format='json' para consumo estruturado",
)

TRUNCATION_NOTICE_PREFIX: Final[str] = "Resposta truncada"
