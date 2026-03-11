from __future__ import annotations

import asyncio
from typing import Any

from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, ErrorData

from app.services.ai_service import AIServiceError, AIServiceNotAvailableError
from app.services.tjdft_client import (
    TJDFTAPIError,
    TJDFTClientError,
    TJDFTConnectionError,
    TJDFTTimeoutError,
)

INVALID_PARAMS_DATA = INVALID_PARAMS
NOT_FOUND = -32004
TIMEOUT = -32001
UPSTREAM_ERROR = -32002
INTERNAL_ERROR_DATA = INTERNAL_ERROR


def build_error(
    code: int,
    message: str,
    *,
    data: dict[str, Any] | None = None,
) -> ErrorData:
    """Cria um ``ErrorData`` padronizado para respostas MCP."""
    return ErrorData(code=code, message=message, data=data)


def as_mcp_error(
    code: int,
    message: str,
    *,
    data: dict[str, Any] | None = None,
) -> McpError:
    """Empacota ``ErrorData`` como ``McpError``."""
    return McpError(build_error(code, message, data=data))


def invalid_params(
    message: str,
    *,
    data: dict[str, Any] | None = None,
) -> McpError:
    """Retorna erro MCP para parâmetros inválidos."""
    return as_mcp_error(
        INVALID_PARAMS_DATA,
        message,
        data={"kind": "invalid_params", **(data or {})},
    )


def not_found(
    message: str,
    *,
    data: dict[str, Any] | None = None,
) -> McpError:
    """Retorna erro MCP para recurso ausente."""
    return as_mcp_error(
        NOT_FOUND,
        message,
        data={"kind": "not_found", **(data or {})},
    )


def timeout(
    message: str = "A operação excedeu o tempo limite.",
    *,
    data: dict[str, Any] | None = None,
) -> McpError:
    """Retorna erro MCP para timeout."""
    return as_mcp_error(
        TIMEOUT,
        message,
        data={"kind": "timeout", "retryable": True, **(data or {})},
    )


def upstream_error(
    message: str,
    *,
    data: dict[str, Any] | None = None,
) -> McpError:
    """Retorna erro MCP para falhas em dependências externas."""
    return as_mcp_error(
        UPSTREAM_ERROR,
        message,
        data={"kind": "upstream_error", "retryable": True, **(data or {})},
    )


def internal_error(
    message: str = "Erro interno ao processar a requisição.",
    *,
    data: dict[str, Any] | None = None,
) -> McpError:
    """Retorna erro MCP para falhas internas não tratadas."""
    return as_mcp_error(
        INTERNAL_ERROR_DATA,
        message,
        data={"kind": "internal_error", **(data or {})},
    )


def to_mcp_error(exc: Exception) -> McpError:
    """Converte exceções comuns do projeto em erros compatíveis com MCP."""
    if isinstance(exc, McpError):
        return exc

    if isinstance(exc, (ValueError, TypeError)):
        return invalid_params(str(exc))

    if isinstance(exc, LookupError):
        return not_found(str(exc))

    if isinstance(exc, (asyncio.TimeoutError, TJDFTTimeoutError)):
        return timeout(str(exc) or "A operação excedeu o tempo limite.")

    if isinstance(exc, AIServiceNotAvailableError):
        return upstream_error(
            str(exc) or "O serviço de IA não está disponível no momento.",
            data={"service": "ai"},
        )

    if isinstance(
        exc,
        (
            AIServiceError,
            TJDFTAPIError,
            TJDFTConnectionError,
            TJDFTClientError,
        ),
    ):
        return upstream_error(str(exc))

    return internal_error(data={"exception_type": type(exc).__name__})
