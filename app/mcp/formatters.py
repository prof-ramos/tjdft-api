"""Utilitários de formatação e truncamento para respostas MCP."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from app.config import Settings
from app.mcp.constants import (
    DEFAULT_TRUNCATION_HINTS,
    TRUNCATION_NOTICE_PREFIX,
    JsonValue,
    ResponseFormat,
)
from app.mcp.schemas import TruncationInfo


def normalize_payload(value: object) -> JsonValue:
    """Converte modelos e tipos comuns para uma estrutura JSON-serializable."""
    if isinstance(value, BaseModel):
        return normalize_payload(value.model_dump(mode="json", exclude_none=True))

    if isinstance(value, Enum):
        return normalize_payload(value.value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Mapping):
        return {str(key): normalize_payload(item) for key, item in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [normalize_payload(item) for item in value]

    return str(value)


def render_json(payload: object) -> str:
    """Serializa payload para JSON estável e legível."""
    return json.dumps(
        normalize_payload(payload),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def build_truncation_message(
    *,
    limit: int,
    original_length: int,
    hints: Sequence[str] | None = None,
) -> str:
    """Monta mensagem acionável para respostas truncadas."""
    resolved_hints = tuple(hints or DEFAULT_TRUNCATION_HINTS)
    actions = "; ".join(resolved_hints)
    return (
        f"{TRUNCATION_NOTICE_PREFIX}: limite de {limit} caracteres atingido "
        f"(original com {original_length} caracteres). Ações sugeridas: {actions}."
    )


def truncate_text(
    text: str,
    *,
    settings: Settings,
    hints: Sequence[str] | None = None,
) -> tuple[str, TruncationInfo | None]:
    """Aplica truncamento textual preservando uma mensagem final acionável."""
    limit = settings.mcp_character_limit
    if len(text) <= limit:
        return text, None

    message = build_truncation_message(
        limit=limit,
        original_length=len(text),
        hints=hints,
    )
    separator = "\n\n"
    reserved = len(message) + len(separator)
    available = max(limit - reserved, 0)
    body = text[:available].rstrip()
    truncated_text = f"{body}{separator}{message}" if body else message[:limit]
    info = TruncationInfo(
        limit=limit,
        original_length=len(text),
        returned_length=len(truncated_text),
        message=message,
        hints=tuple(hints or DEFAULT_TRUNCATION_HINTS),
    )
    return truncated_text, info


def _markdown_lines(value: JsonValue, *, indent: int = 0) -> list[str]:
    """Converte estrutura JSON-serializable em Markdown legível."""
    prefix = "  " * indent

    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}- **{key}**:")
                lines.extend(_markdown_lines(item, indent=indent + 1))
            else:
                rendered = "null" if item is None else str(item)
                lines.append(f"{prefix}- **{key}**: {rendered}")
        return lines or [f"{prefix}- _sem dados_"]

    if isinstance(value, list):
        lines = []
        for index, item in enumerate(value, start=1):
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{index}.")
                lines.extend(_markdown_lines(item, indent=indent + 1))
            else:
                rendered = "null" if item is None else str(item)
                lines.append(f"{prefix}- {rendered}")
        return lines or [f"{prefix}- _sem itens_"]

    rendered = "null" if value is None else str(value)
    return [f"{prefix}{rendered}"]


def render_markdown(payload: object, *, title: str | None = None) -> str:
    """Serializa payload em Markdown simples e estável."""
    normalized = normalize_payload(payload)
    body = "\n".join(_markdown_lines(normalized))
    if title is None:
        return body
    return f"## {title}\n\n{body}"


def format_response(
    payload: object,
    *,
    response_format: ResponseFormat,
    settings: Settings,
    title: str | None = None,
    truncation_hints: Sequence[str] | None = None,
) -> tuple[str, TruncationInfo | None]:
    """Renderiza payload em markdown/json e aplica limite de caracteres."""
    if response_format == ResponseFormat.JSON:
        raw_json = render_json(payload)
        if len(raw_json) <= settings.mcp_character_limit:
            return raw_json, None

        limit = settings.mcp_character_limit
        resolved_hints = list(truncation_hints or DEFAULT_TRUNCATION_HINTS)
        message = build_truncation_message(
            limit=limit,
            original_length=len(raw_json),
            hints=truncation_hints,
        )
        fallback_payload = {
            "truncated": True,
            "message": message,
            "limit": limit,
            "original_length": len(raw_json),
            "preview": "",
            "hints": resolved_hints,
        }

        preview_end = max(limit // 2, 0)
        while True:
            fallback_payload["preview"] = raw_json[:preview_end]
            fallback_json = render_json(fallback_payload)
            if len(fallback_json) <= limit or preview_end == 0:
                info = TruncationInfo(
                    limit=limit,
                    original_length=len(raw_json),
                    returned_length=len(fallback_json),
                    message=message,
                    hints=tuple(resolved_hints),
                )
                return fallback_json, info
            preview_end = max(preview_end - max(limit // 10, 64), 0)

    markdown = render_markdown(payload, title=title)
    return truncate_text(markdown, settings=settings, hints=truncation_hints)
