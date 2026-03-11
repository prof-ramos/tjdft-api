"""
TJDFT API Client - Async HTTP client for TJDFT jurisprudence search API.

This module provides a complete async client for interacting with the TJDFT
(Tribunal de Justiça do Distrito Federal e Territórios) jurisprudence API.
Features: configurable timeouts, retry with exponential backoff, rate limiting,
structured logging, graceful fallbacks, and response validation.
"""

import asyncio
import hashlib
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

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
    pagina: int = 1
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

    Features:
        - Configurable timeouts and retries
        - Exponential backoff retry logic
        - Rate limiting (token bucket)
        - Graceful fallback responses
        - Structured logging
        - Pydantic response validation

    Example:
        >>> cache = CacheManager()
        >>> async with TJDFTClient(cache) as client:
        ...     response = await client.buscar_simples("tributário")
        ...     if response.success:
        ...         print(response.data)
    """

    BASE_URL = "https://jurisdf.tjdft.jus.br/api/v1/pesquisa"

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
        self._client: Optional[httpx.AsyncClient] = None
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
        """
        Async context manager entry.

        Returns:
            Self for use in async with statements
        """
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            ),
            follow_redirects=True,
            headers={
                "User-Agent": "TJDFT-API/1.0",
                "Accept": "application/json",
            }
        )
        logger.debug("AsyncClient created")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.

        Ensures the HTTP client is properly closed.
        """
        if self._client:
            await self._client.aclose()
            logger.debug("AsyncClient closed")

    async def buscar_simples(
        self,
        texto: str,
        pagina: int = 1,
        tamanho_pagina: int = 20,
    ) -> TJDFTResponse:
        """
        Busca simples por texto com fallback graceful.

        Args:
            texto: Termo de busca
            pagina: Número da página (default: 1)
            tamanho_pagina: Tamanho da página (default: 20)

        Returns:
            TJDFTResponse com resultado ou erro
        """
        if not texto or not texto.strip():
            return TJDFTResponse(
                success=False,
                error="Query parameter cannot be empty",
                fallback=True
            )

        try:
            # Tenta cache primeiro
            cache_key = f"busca:{texto}:{pagina}:{tamanho_pagina}"
            cached = await self._cache.get(cache_key)

            if cached:
                logger.info(
                    "Cache hit",
                    extra={"extra_data": {
                        "query": texto,
                        "pagina": pagina,
                        "cache_hit": True,
                    }}
                )
                # Handle both dict and JSON string from cache
                if isinstance(cached, str):
                    cached = json.loads(cached)
                return TJDFTResponse(success=True, data=cached, cached=True)

            # Rate limiting
            async with self._rate_limiter:
                params = {
                    "q": texto.strip(),
                    "pagina": pagina,
                    "tamanho": tamanho_pagina,
                }

                dados = await self._request_with_retry("GET", "", params=params)

                # Valida resposta
                if not self._validate_response(dados):
                    logger.warning(
                        "Resposta inválida do TJDFT",
                        extra={"extra_data": {"query": texto}}
                    )
                    return TJDFTResponse(
                        success=False,
                        error="Resposta do TJDFT em formato inesperado",
                        fallback=True
                    )

                # Atualiza cache
                await self._cache.set(cache_key, dados, ttl=3600)

                logger.info(
                    "Busca concluída com sucesso",
                    extra={"extra_data": {
                        "query": texto,
                        "pagina": pagina,
                        "results": len(dados.get("dados", [])),
                        "cache_hit": False,
                    }}
                )

                return TJDFTResponse(success=True, data=dados)

        except TJDFTConnectionError as e:
            logger.error(
                f"Erro de conexão: {e}",
                extra={"extra_data": {"query": texto}}
            )
            return TJDFTResponse(
                success=False,
                error="API do TJDFT indisponível. Tente novamente mais tarde.",
                fallback=True
            )
        except Exception as e:
            logger.exception(
                f"Erro inesperado: {e}",
                extra={"extra_data": {"query": texto}}
            )
            return TJDFTResponse(
                success=False,
                error=f"Erro interno: {str(e)}",
                fallback=True
            )

    async def buscar_com_filtros(
        self,
        query: str,
        relator: Optional[str] = None,
        classe: Optional[str] = None,
        orgao_julgador: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        pagina: int = 1,
        tamanho_pagina: int = 20,
    ) -> TJDFTResponse:
        """
        Busca com filtros avançados e fallback graceful.

        Args:
            query: Termo de busca
            relator: Nome do relator (filtro opcional)
            classe: Classe processual (filtro opcional)
            orgao_julgador: Órgão julgador (filtro opcional)
            data_inicio: Data início (formato ISO, filtro opcional)
            data_fim: Data fim (formato ISO, filtro opcional)
            pagina: Número da página (default: 1)
            tamanho_pagina: Tamanho da página (default: 20)

        Returns:
            TJDFTResponse com resultado ou erro
        """
        if not query or not query.strip():
            return TJDFTResponse(
                success=False,
                error="Query parameter cannot be empty",
                fallback=True
            )

        try:
            # Tenta cache primeiro
            params_hash = hashlib.md5(
                json.dumps({
                    "q": query.strip(),
                    "relator": relator,
                    "classe": classe,
                    "orgao_julgador": orgao_julgador,
                    "data_inicio": data_inicio,
                    "data_fim": data_fim,
                    "pagina": pagina,
                    "tamanho": tamanho_pagina,
                }, sort_keys=True).encode()
            ).hexdigest()[:8]

            cache_key = f"busca:filtros:{params_hash}"
            cached = await self._cache.get(cache_key)

            if cached:
                logger.info(
                    "Cache hit (filtros)",
                    extra={"extra_data": {
                        "query": query,
                        "pagina": pagina,
                        "cache_hit": True,
                    }}
                )
                if isinstance(cached, str):
                    cached = json.loads(cached)
                return TJDFTResponse(success=True, data=cached, cached=True)

            # Rate limiting
            async with self._rate_limiter:
                params = {
                    "q": query.strip(),
                    "pagina": pagina,
                    "tamanho": tamanho_pagina,
                }

                # Add optional filters
                if relator:
                    params["relator"] = relator
                if classe:
                    params["classe"] = classe
                if orgao_julgador:
                    params["orgao_julgador"] = orgao_julgador
                if data_inicio:
                    params["data_inicio"] = data_inicio
                if data_fim:
                    params["data_fim"] = data_fim

                dados = await self._request_with_retry("GET", "", params=params)

                # Valida resposta
                if not self._validate_response(dados):
                    logger.warning(
                        "Resposta inválida do TJDFT (filtros)",
                        extra={"extra_data": {"query": query}}
                    )
                    return TJDFTResponse(
                        success=False,
                        error="Resposta do TJDFT em formato inesperado",
                        fallback=True
                    )

                # Atualiza cache
                await self._cache.set(cache_key, dados, ttl=3600)

                logger.info(
                    "Busca com filtros concluída",
                    extra={"extra_data": {
                        "query": query,
                        "pagina": pagina,
                        "results": len(dados.get("dados", [])),
                    }}
                )

                return TJDFTResponse(success=True, data=dados)

        except TJDFTConnectionError as e:
            logger.error(
                f"Erro de conexão (filtros): {e}",
                extra={"extra_data": {"query": query}}
            )
            return TJDFTResponse(
                success=False,
                error="API do TJDFT indisponível. Tente novamente mais tarde.",
                fallback=True
            )
        except Exception as e:
            logger.exception(
                f"Erro inesperado (filtros): {e}",
                extra={"extra_data": {"query": query}}
            )
            return TJDFTResponse(
                success=False,
                error=f"Erro interno: {str(e)}",
                fallback=True
            )

    async def buscar_todas_paginas(
        self,
        query: str,
        max_paginas: int = 10,
        tamanho_pagina: int = 20,
        **filtros
    ) -> TJDFTResponse:
        """
        Busca todas as páginas automaticamente.

        Args:
            query: Termo de busca
            max_paginas: Número máximo de páginas a buscar (default: 10)
            tamanho_pagina: Tamanho da página (default: 20)
            **filtros: Filtros adicionais (relator, classe, etc.)

        Returns:
            TJDFTResponse com todos os resultados ou erro
        """
        try:
            all_results = []
            pagina = 1

            logger.info(
                "Multi-page search iniciada",
                extra={"extra_data": {
                    "query": query,
                    "max_pages": max_paginas,
                }}
            )

            while pagina <= max_paginas:
                # Check if we have filters
                if filtros:
                    response = await self.buscar_com_filtros(
                        query=query,
                        pagina=pagina,
                        tamanho_pagina=tamanho_pagina,
                        **filtros
                    )
                else:
                    response = await self.buscar_simples(
                        texto=query,
                        pagina=pagina,
                        tamanho_pagina=tamanho_pagina
                    )

                if not response.success:
                    return response

                # Extract data
                dados = response.data.get("dados", [])

                if not dados:
                    logger.info(
                        f"No more results at page {pagina}",
                        extra={"extra_data": {"pagina": pagina}}
                    )
                    break

                all_results.extend(dados)
                logger.info(
                    f"Retrieved {len(dados)} results from page {pagina}",
                    extra={"extra_data": {"pagina": pagina}}
                )

                # Check if there are more pages
                paginacao = response.data.get("paginacao", {})
                total = paginacao.get("total", 0)
                pagina_size = paginacao.get("tamanho", tamanho_pagina)

                if len(all_results) >= total:
                    logger.info(
                        f"Retrieved all {len(all_results)} results",
                        extra={"extra_data": {"total_results": len(all_results)}}
                    )
                    break

                pagina += 1

                # Small delay between pages
                await asyncio.sleep(0.1)

            logger.info(
                "Multi-page search concluída",
                extra={"extra_data": {"total_results": len(all_results)}}
            )

            return TJDFTResponse(
                success=True,
                data={"dados": all_results, "total": len(all_results)}
            )

        except Exception as e:
            logger.exception(
                f"Erro inesperado (multi-page): {e}",
                extra={"extra_data": {"query": query}}
            )
            return TJDFTResponse(
                success=False,
                error=f"Erro interno: {str(e)}",
                fallback=True
            )

    async def get_metadata(self) -> TJDFTResponse:
        """
        Obtém metadados da API (filtros disponíveis).

        Returns:
            TJDFTResponse com metadados ou erro
        """
        cache_key = "tjdft:metadata"

        try:
            # Tenta cache primeiro
            cached = await self._cache.get(cache_key)

            if cached:
                logger.info("Metadata cache hit")
                if isinstance(cached, str):
                    cached = json.loads(cached)
                return TJDFTResponse(success=True, data=cached, cached=True)

            # Rate limiting
            async with self._rate_limiter:
                metadata = await self._request_with_retry("GET", self.BASE_URL)

                # Cache metadata for longer (24 hours)
                await self._cache.set(cache_key, metadata, ttl=86400)

                logger.info("Metadata retrieved successfully")
                return TJDFTResponse(success=True, data=metadata)

        except TJDFTConnectionError as e:
            logger.error(f"Erro de conexão (metadata): {e}")
            return TJDFTResponse(
                success=False,
                error="API do TJDFT indisponível. Tente novamente mais tarde.",
                fallback=True
            )
        except Exception as e:
            logger.exception(f"Erro inesperado (metadata): {e}")
            return TJDFTResponse(
                success=False,
                error=f"Erro interno: {str(e)}",
                fallback=True
            )

    # ==========================================
    # Private Methods
    # ==========================================

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> dict:
        """
        Request com retry automático e backoff exponencial.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL completa ou endpoint
            **kwargs: Additional arguments for httpx.request

        Returns:
            Dict com a resposta da API

        Raises:
            TJDFTConnectionError: Erro de conexão após retries
        """
        last_exception = None
        full_url = url if url.startswith("http") else f"{self.BASE_URL}/{url}".rstrip("/")

        for attempt in range(self.max_retries):
            try:
                if not self._client:
                    raise RuntimeError("Client not initialized. Use 'async with' statement.")

                logger.debug(
                    f"Making request (attempt {attempt + 1}/{self.max_retries})",
                    extra={"extra_data": {
                        "method": method,
                        "url": full_url,
                        "attempt": attempt + 1,
                    }}
                )

                response = await self._client.request(method, full_url, **kwargs)
                response.raise_for_status()

                data = response.json()

                # Normalize response format
                result = {
                    "dados": self._extract_results(data),
                    "paginacao": self._extract_pagination(data, kwargs.get("params", {})),
                    "sucesso": True,
                }

                logger.debug(
                    f"Request successful",
                    extra={"extra_data": {"results": len(result["dados"])}}
                )

                return result

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Retry {attempt + 1}/{self.max_retries} em {delay}s: {e}",
                        extra={"extra_data": {"delay": delay, "error": str(e)}}
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    last_exception = e
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Server error {e.response.status_code}, retry em {delay}s",
                            extra={"extra_data": {
                                "status_code": e.response.status_code,
                                "delay": delay,
                            }}
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise

                # Client errors - don't retry
                logger.error(
                    f"Client error {e.response.status_code}",
                    extra={"extra_data": {"status_code": e.response.status_code}}
                )
                raise TJDFTAPIError(
                    f"API client error: {e.response.status_code} - {e.response.text}"
                ) from e

        raise TJDFTConnectionError(
            f"Failed after {self.max_retries} retries: {last_exception}"
        )

    def _validate_response(self, data: dict) -> bool:
        """
        Valida se resposta do TJDFT está no formato esperado.

        Args:
            data: Dados da resposta

        Returns:
            True se válido, False caso contrário
        """
        try:
            TJDFTSearchResult(
                total=data.get("paginacao", {}).get("total", 0),
                itens=[TJDFTItem(**item) for item in data.get("dados", [])],
                pagina=data.get("paginacao", {}).get("pagina", 1),
                tamanho_pagina=data.get("paginacao", {}).get("tamanho", 20)
            )
            return True
        except ValidationError as e:
            logger.warning(
                f"Resposta inválida do TJDFT: {e}",
                extra={"extra_data": {"validation_error": str(e)}}
            )
            return False

    def _extract_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrai a lista de resultados da resposta da API.

        Args:
            data: Dados brutos da API

        Returns:
            Lista de resultados (pode estar vazia)
        """
        # Try common result key names
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            for key in ["dados", "results", "items", "data"]:
                if key in data and isinstance(data[key], list):
                    return data[key]

        # If no results found, return empty list
        logger.warning(
            f"Could not extract results from API response: {type(data)}"
        )
        return []

    def _extract_pagination(
        self,
        data: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extrai informações de paginação da resposta da API.

        Args:
            data: Dados brutos da API
            params: Parâmetros da requisição

        Returns:
            Dict com informações de paginação
        """
        paginacao = {
            "pagina": params.get("pagina", 1),
            "tamanho": params.get("tamanho", params.get("tamanho_pagina", 20)),
            "total": 0,
        }

        if isinstance(data, dict):
            # Try to extract pagination info
            for key in ["paginacao", "pagination", "meta"]:
                if key in data and isinstance(data[key], dict):
                    paginacao.update(data[key])
                    break

            # Try to get total from data length
            results = self._extract_results(data)
            if results and "total" not in paginacao:
                paginacao["total"] = len(results)

        return paginacao
