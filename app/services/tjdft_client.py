"""
TJDFT API Client - Async HTTP client for TJDFT jurisprudence search API.

This module provides a complete async client for interacting with the TJDFT
(Tribunal de Justiça do Distrito Federal e Territórios) jurisprudence API.
"""

import asyncio
import hashlib
import json
import logging
from typing import Optional, List, Dict, Any

from httpx import (
    AsyncClient,
    Timeout,
    ConnectError,
    TimeoutException,
    HTTPStatusError,
)

from app.utils.cache import CacheManager

logger = logging.getLogger(__name__)


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


class TJDFTClient:
    """
    Cliente assíncrono para API de pesquisa do TJDFT.

    This client provides async methods to search jurisprudence with caching,
    retry logic with exponential backoff, and comprehensive error handling.

    Example:
        >>> cache = CacheManager()
        >>> async with TJDFTClient(cache) as client:
        ...     results = await client.buscar_simples("tributário")
        ...     print(results)
    """

    BASE_URL = "https://jurisdf.tjdft.jus.br/api/v1/pesquisa"
    MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 30.0
    CONNECT_TIMEOUT = 10.0

    def __init__(
        self,
        cache_manager: CacheManager,
        timeout: float = DEFAULT_TIMEOUT,
        connect_timeout: float = CONNECT_TIMEOUT,
    ):
        """
        Initialize TJDFT client.

        Args:
            cache_manager: CacheManager instance for caching responses
            timeout: Request timeout in seconds (default: 30.0)
            connect_timeout: Connection timeout in seconds (default: 10.0)
        """
        self.cache = cache_manager
        self.client: Optional[AsyncClient] = None
        self.timeout = Timeout(timeout, connect=connect_timeout)
        logger.info(f"TJDFTClient initialized with timeout={timeout}s")

    async def __aenter__(self):
        """
        Async context manager entry.

        Returns:
            Self for use in async with statements
        """
        self.client = AsyncClient(
            timeout=self.timeout,
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
        if self.client:
            await self.client.aclose()
            logger.debug("AsyncClient closed")

    async def buscar_simples(
        self,
        query: str,
        pagina: int = 1,
        tamanho: int = 20,
    ) -> Dict[str, Any]:
        """
        Busca simples por texto na API do TJDFT.

        Args:
            query: Termo de busca
            pagina: Número da página (default: 1)
            tamanho: Tamanho da página (default: 20)

        Returns:
            Dict contendo os resultados da busca com chaves:
            - dados: Lista de resultados
            - paginacao: Info de paginação (total, pagina, tamanho)
            - sucesso: Boolean indicando sucesso

        Raises:
            TJDFTConnectionError: Erro de conexão
            TJDFTTimeoutError: Erro de timeout
            TJDFTAPIError: Erro da API
        """
        if not query or not query.strip():
            raise ValueError("Query parameter cannot be empty")

        params = {
            "q": query.strip(),
            "pagina": pagina,
            "tamanho": tamanho,
        }

        cache_key = self._build_cache_key("simples", params)

        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for key: {cache_key}")
            # Handle both dict and JSON string from cache
            if isinstance(cached, str):
                import json
                return json.loads(cached)
            return cached

        # Make request
        result = await self._make_request("", params)

        # Cache the result
        self.cache.set(cache_key, result, ttl=3600)

        return result

    async def buscar_com_filtros(
        self,
        query: str,
        relator: Optional[str] = None,
        classe: Optional[str] = None,
        orgao_julgador: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        pagina: int = 1,
        tamanho: int = 20,
    ) -> Dict[str, Any]:
        """
        Busca com filtros avançados na API do TJDFT.

        Args:
            query: Termo de busca
            relator: Nome do relator (filtro opcional)
            classe: Classe processual (filtro opcional)
            orgao_julgador: Órgão julgador (filtro opcional)
            data_inicio: Data início (formato ISO, filtro opcional)
            data_fim: Data fim (formato ISO, filtro opcional)
            pagina: Número da página (default: 1)
            tamanho: Tamanho da página (default: 20)

        Returns:
            Dict contendo os resultados da busca

        Raises:
            TJDFTConnectionError: Erro de conexão
            TJDFTTimeoutError: Erro de timeout
            TJDFTAPIError: Erro da API
        """
        if not query or not query.strip():
            raise ValueError("Query parameter cannot be empty")

        params = {
            "q": query.strip(),
            "pagina": pagina,
            "tamanho": tamanho,
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

        cache_key = self._build_cache_key("filtrada", params)

        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for key: {cache_key}")
            # Handle both dict and JSON string from cache
            if isinstance(cached, str):
                import json
                return json.loads(cached)
            return cached

        # Make request
        result = await self._make_request("", params)

        # Cache the result
        self.cache.set(cache_key, result, ttl=3600)

        return result

    async def buscar_todas_paginas(
        self,
        query: str,
        max_paginas: int = 10,
        tamanho: int = 20,
        **filtros
    ) -> List[Dict[str, Any]]:
        """
        Busca todas as páginas automaticamente.

        Este método faz paginação automática e retorna todos os resultados
        de todas as páginas até max_paginas.

        Args:
            query: Termo de busca
            max_paginas: Número máximo de páginas a buscar (default: 10)
            tamanho: Tamanho da página (default: 20)
            **filtros: Filtros adicionais (relator, classe, etc.)

        Returns:
            Lista de todos os resultados encontrados

        Raises:
            TJDFTConnectionError: Erro de conexão
            TJDFTTimeoutError: Erro de timeout
            TJDFTAPIError: Erro da API
        """
        all_results = []
        pagina = 1

        logger.info(f"Starting multi-page search: query='{query}', max_pages={max_paginas}")

        while pagina <= max_paginas:
            # Check if we have filters
            if filtros:
                result = await self.buscar_com_filtros(
                    query=query,
                    pagina=pagina,
                    tamanho=tamanho,
                    **filtros
                )
            else:
                result = await self.buscar_simples(
                    query=query,
                    pagina=pagina,
                    tamanho=tamanho
                )

            # Extract data
            dados = result.get("dados", [])

            if not dados:
                logger.info(f"No more results at page {pagina}")
                break

            all_results.extend(dados)
            logger.info(f"Retrieved {len(dados)} results from page {pagina}")

            # Check if there are more pages
            paginacao = result.get("paginacao", {})
            total = paginacao.get("total", 0)
            pagina_size = paginacao.get("tamanho", tamanho)

            if len(all_results) >= total:
                logger.info(f"Retrieved all {len(all_results)} results")
                break

            pagina += 1

            # Small delay between pages to be polite
            await asyncio.sleep(0.1)

        logger.info(f"Multi-page search completed: {len(all_results)} total results")
        return all_results

    def _build_cache_key(self, search_type: str, params: Dict[str, Any]) -> str:
        """
        Gera chave de cache baseada nos parâmetros da busca.

        Args:
            search_type: Tipo de busca (simples, filtrada)
            params: Dicionário de parâmetros

        Returns:
            String representando a chave única de cache
        """
        # Create a deterministic string from params
        sorted_params = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:8]

        return f"tjdft:{search_type}:{params_hash}"

    async def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Faz request com retry logic e exponential backoff.

        Args:
            endpoint: Endpoint da API (vazio para busca principal)
            params: Parâmetros da requisição

        Returns:
            Dict com a resposta da API

        Raises:
            TJDFTConnectionError: Erro de conexão após retries
            TJDFTTimeoutError: Timeout após retries
            TJDFTAPIError: Erro da API após retries
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' statement.")

        url = f"{self.BASE_URL}/{endpoint}".rstrip("/")

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.debug(f"Making request to {url} (attempt {attempt}/{self.MAX_RETRIES})")
                logger.debug(f"Params: {params}")

                response = await self.client.get(url, params=params)
                response.raise_for_status()

                data = response.json()

                # Normalize response format
                result = {
                    "dados": self._extract_results(data),
                    "paginacao": self._extract_pagination(data, params),
                    "sucesso": True,
                }

                logger.debug(f"Request successful: {len(result['dados'])} results")
                return result

            except ConnectError as e:
                logger.warning(f"Connection error (attempt {attempt}/{self.MAX_RETRIES}): {e}")

                if attempt == self.MAX_RETRIES:
                    raise TJDFTConnectionError(
                        f"Failed to connect after {self.MAX_RETRIES} attempts"
                    ) from e

                # Exponential backoff
                delay = 2 ** attempt
                logger.debug(f"Retrying after {delay}s...")
                await asyncio.sleep(delay)

            except TimeoutException as e:
                logger.warning(f"Timeout error (attempt {attempt}/{self.MAX_RETRIES}): {e}")

                if attempt == self.MAX_RETRIES:
                    raise TJDFTTimeoutError(
                        f"Request timed out after {self.MAX_RETRIES} attempts"
                    ) from e

                # Exponential backoff
                delay = 2 ** attempt
                logger.debug(f"Retrying after {delay}s...")
                await asyncio.sleep(delay)

            except HTTPStatusError as e:
                logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")

                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise TJDFTAPIError(
                        f"API client error: {e.response.status_code} - {e.response.text}"
                    ) from e

                # Retry server errors (5xx)
                if attempt == self.MAX_RETRIES:
                    raise TJDFTAPIError(
                        f"API server error after {self.MAX_RETRIES} attempts: "
                        f"{e.response.status_code}"
                    ) from e

                # Exponential backoff
                delay = 2 ** attempt
                logger.debug(f"Retrying after {delay}s...")
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise TJDFTClientError(f"Unexpected error: {e}") from e

        # Should never reach here
        raise TJDFTClientError("Failed to complete request")

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
        logger.warning(f"Could not extract results from API response: {type(data)}")
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
            "tamanho": params.get("tamanho", 20),
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

    async def get_metadata(self) -> Dict[str, Any]:
        """
        Obtém metadados da API (filtros disponíveis).

        Returns:
            Dict com metadados da API (relatores, classes, orgaos, etc.)

        Raises:
            TJDFTConnectionError: Erro de conexão
            TJDFTTimeoutError: Erro de timeout
            TJDFTAPIError: Erro da API
        """
        cache_key = "tjdft:metadata"

        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug("Metadata cache hit")
            # Handle both dict and JSON string from cache
            if isinstance(cached, str):
                import json
                return json.loads(cached)
            return cached

        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' statement.")

        try:
            logger.debug(f"Fetching metadata from {self.BASE_URL}")
            response = await self.client.get(self.BASE_URL)
            response.raise_for_status()

            metadata = response.json()

            # Cache metadata for longer (24 hours)
            self.cache.set(cache_key, metadata, ttl=86400)

            logger.debug("Metadata retrieved successfully")
            return metadata

        except ConnectError as e:
            raise TJDFTConnectionError(f"Failed to connect: {e}") from e
        except TimeoutException as e:
            raise TJDFTTimeoutError(f"Request timed out: {e}") from e
        except HTTPStatusError as e:
            raise TJDFTAPIError(
                f"API error: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise TJDFTClientError(f"Unexpected error: {e}") from e
