"""
TJDFT API Client - Async HTTP client for TJDFT jurisprudence search API.

This module provides a complete async client for interacting with the TJDFT
(Tribunal de Justiça do Distrito Federal e Territórios) jurisprudence API.
Features: configurable timeouts, retry with exponential backoff, rate limiting,
structured logging, graceful fallbacks, and response validation.

API Details:
    - Busca:     POST https://jurisdf.tjdft.jus.br/api/v1/pesquisa
    - Metadados: GET  https://jurisdf.tjdft.jus.br/api/v1/pesquisa
    - Cobre apenas acórdãos (2ª instância)
    - Paginação 0-indexed, máx 40 resultados por página
"""

import asyncio
import hashlib
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, cast, Union

import httpx
from pydantic import BaseModel, ValidationError

from app.utils.cache import CacheManager


# ==========================================
# Structured Logging Configuration
# ==========================================

logger = logging.getLogger("tjdft_client")
logger.setLevel(logging.INFO)


class StructuredFormatter(logging.Formatter):
    """Formatter para logs estruturados em JSON."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        return json.dumps(log_data)


# ==========================================
# Response Models with Pydantic Validation
# ==========================================

class TJDFTItem(BaseModel):
    """Schema de item retornado pelo TJDFT."""
    id: Optional[str] = None
    numero_processo: Optional[str] = None
    ementa: Optional[str] = None
    relator: Optional[str] = None
    data_julgamento: Optional[str] = None
    orgao_julgador: Optional[str] = None
    classe: Optional[str] = None


class TJDFTSearchResult(BaseModel):
    """Schema de resposta de busca."""
    total: int = 0
    itens: List[TJDFTItem] = []
    pagina: int = 0
    tamanho_pagina: int = 20


# ==========================================
# Graceful Fallback Response
# ==========================================

@dataclass
class TJDFTResponse:
    """Resposta padrão com fallback graceful."""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    cached: bool = False
    fallback: bool = False


# ==========================================
# Rate Limiter com Token Bucket
# ==========================================

class RateLimiter:
    """Rate limiter com token bucket."""

    def __init__(self, rate: float = 2.0):
        """
        Inicializa rate limiter.

        Args:
            rate: Número de requisições por segundo (default: 2.0)
        """
        self.rate = rate
        self._tokens = rate
        self._last_update = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Adquire um token do bucket."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_update
            self._tokens = min(self.rate, self._tokens + elapsed * self.rate)

            if self._tokens < 1:
                wait_time = (1 - self._tokens) / self.rate
                await asyncio.sleep(wait_time)
                self._tokens = 0
            else:
                self._tokens -= 1

            self._last_update = asyncio.get_event_loop().time()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# ==========================================
# Custom Exceptions
# ==========================================

class TJDFTClientError(Exception):
    """Base exception for TJDFT client errors."""
    pass


class TJDFTConnectionError(TJDFTClientError):
    """Connection error exception."""
    pass


class TJDFTTimeoutError(TJDFTClientError):
    """Timeout error exception."""
    pass


class TJDFTAPIError(TJDFTClientError):
    """API error exception."""
    pass


# ==========================================
# Main TJDFT Client
# ==========================================

class TJDFTClient:
    """
    Cliente assíncrono para API de pesquisa do TJDFT.

    Realiza buscas de acórdãos via POST com suporte a filtros por relator,
    classe processual e órgão julgador. Inclui cache, retry com backoff
    exponencial, rate limiting e tratamento de erros.

    Features:
        - Configurable timeouts and retries
        - Exponential backoff retry logic
        - Rate limiting (token bucket)
        - Graceful fallback responses
        - Structured logging
        - Pydantic response validation
    """

    BASE_URL = "https://jurisdf.tjdft.jus.br/api/v1/pesquisa"
    MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 30.0
    CONNECT_TIMEOUT = 10.0
    MAX_TAMANHO = 40

    def __init__(
        self,
        cache_manager: CacheManager,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit: float = 2.0,
    ):
        """
        Initialize TJDFT client with configurable parameters.

        Args:
            cache_manager: CacheManager instance for caching responses
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Base delay for retries in seconds (default: 1.0)
            rate_limit: Rate limit in requests/second (default: 2.0)
        """
        self.cache = cache_manager
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter(rate=rate_limit)

        logger.info(
            "TJDFTClient initialized",
            extra={"extra_data": {
                "timeout": timeout,
                "max_retries": max_retries,
                "retry_delay": retry_delay,
                "rate_limit": rate_limit,
            }}
        )

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, connect=self.CONNECT_TIMEOUT),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            ),
            follow_redirects=True,
            headers={
                "User-Agent": "TJDFT-API/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
            logger.debug("AsyncClient closed")
            self.client = None

    async def buscar_simples(
        self,
        query: str,
        pagina: int = 0,
        tamanho: int = 20,
    ) -> Union[Dict[str, Any], TJDFTResponse]:
        """
        Busca acórdãos por texto livre com suporte a fallback.

        Args:
            query: Termo de busca (pode ser vazio).
            pagina: Página (0-indexed).
            tamanho: Resultados por página (máx 40).

        Returns:
            Dict ou TJDFTResponse com resultados.
        """
        if not isinstance(query, str):
            return TJDFTResponse(success=False, error="Query must be a string", fallback=True)

        tamanho = min(tamanho, self.MAX_TAMANHO)
        payload = {"query": query, "pagina": pagina, "tamanho": tamanho}
        cache_key = self._build_cache_key("simples", payload)

        try:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit: {cache_key}")
                data = json.loads(cached) if isinstance(cached, str) else cached
                return TJDFTResponse(success=True, data=data, cached=True)

            async with self._rate_limiter:
                data = await self._post(payload)
                result = self._normalize_response(data, pagina, tamanho)

                # Validate response
                if not self._validate_response(result):
                    return TJDFTResponse(success=False, error="Invalid API response format", fallback=True)

                self.cache.set(cache_key, result, ttl=3600)
                return TJDFTResponse(success=True, data=result)

        except (TJDFTConnectionError, TJDFTTimeoutError) as e:
            logger.error(f"Network error in buscar_simples: {e}")
            return TJDFTResponse(success=False, error=str(e), fallback=True)
        except Exception as e:
            logger.exception(f"Unexpected error in buscar_simples: {e}")
            return TJDFTResponse(success=False, error=f"Internal error: {str(e)}", fallback=True)

    async def buscar_com_filtros(
        self,
        query: str = "",
        relator: Optional[str] = None,
        classe: Optional[str] = None,
        orgao_julgador: Optional[str] = None,
        base: Optional[str] = None,
        subbase: Optional[str] = None,
        revisor: Optional[str] = None,
        relator_designado: Optional[str] = None,
        processo: Optional[str] = None,
        pagina: int = 0,
        tamanho: int = 20,
    ) -> TJDFTResponse:
        """Busca com filtros avançados e fallback graceful."""
        tamanho = min(tamanho, self.MAX_TAMANHO)

        termos = []
        if relator: termos.append({"campo": "nomeRelator", "valor": relator})
        if classe: termos.append({"campo": "descricaoClasseCnj", "valor": classe})
        if orgao_julgador: termos.append({"campo": "descricaoOrgaoJulgador", "valor": orgao_julgador})
        if base: termos.append({"campo": "base", "valor": base})
        if subbase: termos.append({"campo": "subbase", "valor": subbase})
        if revisor: termos.append({"campo": "nomeRevisor", "valor": revisor})
        if relator_designado: termos.append({"campo": "nomeRelatorDesignado", "valor": relator_designado})
        if processo: termos.append({"campo": "processo", "valor": processo})

        payload = {"query": query, "pagina": pagina, "tamanho": tamanho}
        if termos:
            payload["termosAcessorios"] = termos

        cache_key = self._build_cache_key("filtrada", payload)

        try:
            cached = self.cache.get(cache_key)
            if cached:
                data = json.loads(cached) if isinstance(cached, str) else cached
                return TJDFTResponse(success=True, data=data, cached=True)

            async with self._rate_limiter:
                data = await self._post(payload)
                result = self._normalize_response(data, pagina, tamanho)

                if not self._validate_response(result):
                    return TJDFTResponse(success=False, error="Invalid response format", fallback=True)

                self.cache.set(cache_key, result, ttl=3600)
                return TJDFTResponse(success=True, data=result)

        except Exception as e:
            logger.error(f"Error in buscar_com_filtros: {e}")
            return TJDFTResponse(success=False, error=str(e), fallback=True)

    async def buscar_todas_paginas(
        self,
        query: str = "",
        max_paginas: int = 10,
        tamanho: int = 40,
        **filtros,
    ) -> Union[List[Dict[str, Any]], TJDFTResponse]:
        """Coleta acórdãos de múltiplas páginas automaticamente."""
        all_registros = []
        tamanho = min(tamanho, self.MAX_TAMANHO)

        logger.info(f"Multi-page search: query='{query}', max={max_paginas}")

        for pagina in range(max_paginas):
            response = await self.buscar_com_filtros(
                query=query, pagina=pagina, tamanho=tamanho, **filtros
            )

            if not response.success:
                if all_registros: # Return partial if we have something
                    return all_registros
                return response

            registros = response.data.get("registros", [])
            if not registros:
                break

            all_registros.extend(registros)
            total = response.data.get("total", 0)
            if len(all_registros) >= total:
                break

            await asyncio.sleep(0.1)

        return all_registros

    async def get_metadata(self) -> Union[Dict[str, Any], TJDFTResponse]:
        """Obtém listas de valores válidos para filtros."""
        cache_key = "tjdft:metadata"

        try:
            cached = self.cache.get(cache_key)
            if cached:
                return TJDFTResponse(success=True, data=json.loads(cached) if isinstance(cached, str) else cached, cached=True)

            if not self.client:
                raise RuntimeError("Client not initialized")

            metadata = await self._request_with_retry("GET", self.BASE_URL)
            self.cache.set(cache_key, metadata, ttl=86400)
            return TJDFTResponse(success=True, data=metadata)

        except Exception as e:
            return TJDFTResponse(success=False, error=str(e), fallback=True)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_cache_key(self, search_type: str, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        h = hashlib.md5(serialized.encode()).hexdigest()[:8]
        return f"tjdft:{search_type}:{h}"

    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Realiza POST com retry automático."""
        return await self._request_with_retry("POST", self.BASE_URL, json=payload)

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Request com retry e backoff exponencial."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return cast(Dict[str, Any], response.json())

            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                if isinstance(e, httpx.TimeoutException):
                    raise TJDFTTimeoutError(f"Timeout after {self.max_retries} attempts")
                raise TJDFTConnectionError(f"Connection failed: {e}")

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                raise TJDFTAPIError(f"API Error {e.response.status_code}: {e.response.text}")

        raise TJDFTClientError(f"Failed after {self.max_retries} retries: {last_exception}")

    def _validate_response(self, data: dict) -> bool:
        """Valida se resposta está no formato esperado (opcional para simplicidade interna)."""
        return "registros" in data or "itens" in data

    def _normalize_response(
        self, data: Dict[str, Any], pagina: int, tamanho: int
    ) -> Dict[str, Any]:
        """Normaliza a resposta da API para formato consistente."""
        return {
            "registros": data.get("registros", []),
            "total": data.get("hits", {}).get("value", 0),
            "pagina": pagina,
            "tamanho": tamanho,
            "agregacoes": data.get("agregacoes", {}),
        }
