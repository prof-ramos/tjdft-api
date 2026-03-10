"""
TJDFT API Client - Async HTTP client for TJDFT jurisprudence search API.

This module provides a complete async client for interacting with the TJDFT
(Tribunal de Justiça do Distrito Federal e Territórios) jurisprudence API.

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
from typing import Any, Dict, List, Optional, cast

from httpx import (
    AsyncClient,
    ConnectError,
    HTTPStatusError,
    Timeout,
    TimeoutException,
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

    Realiza buscas de acórdãos via POST com suporte a filtros por relator,
    classe processual e órgão julgador. Inclui cache, retry com backoff
    exponencial e tratamento de erros.

    Example:
        >>> cache = CacheManager()
        >>> async with TJDFTClient(cache) as client:
        ...     results = await client.buscar_simples("tributário")
        ...     print(results["total"], "acórdãos encontrados")
        ...     for r in results["registros"]:
        ...         print(r["dataJulgamento"], r["processo"])
    """

    BASE_URL = "https://jurisdf.tjdft.jus.br/api/v1/pesquisa"
    MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 30.0
    CONNECT_TIMEOUT = 10.0
    MAX_TAMANHO = 40

    def __init__(
        self,
        cache_manager: CacheManager,
        timeout: float = DEFAULT_TIMEOUT,
        connect_timeout: float = CONNECT_TIMEOUT,
    ):
        self.cache = cache_manager
        self.client: Optional[AsyncClient] = None
        self.timeout = Timeout(timeout, connect=connect_timeout)
        logger.info(f"TJDFTClient initialized with timeout={timeout}s")

    async def __aenter__(self):
        self.client = AsyncClient(
            timeout=self.timeout,
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
            try:
                await self.client.aclose()
            finally:
                self.client = None

    async def buscar_simples(
        self,
        query: str,
        pagina: int = 0,
        tamanho: int = 20,
    ) -> Dict[str, Any]:
        """
        Busca acórdãos por texto livre.

        Args:
            query: Termo de busca em linguagem natural. Pode ser vazio ("") para
                   retornar todos os acórdãos sem filtro de tema.
            pagina: Página (0-indexed). Default: 0.
            tamanho: Resultados por página. Mín: 1, Máx: 40. Default: 20.

        Returns:
            Dict com:
            - registros: Lista de acórdãos
            - total: Total de acórdãos encontrados
            - pagina: Página atual
            - tamanho: Tamanho da página
            - agregacoes: Agregações por relator, classe, órgão etc.

        Raises:
            TJDFTConnectionError: Erro de conexão
            TJDFTTimeoutError: Timeout
            TJDFTAPIError: Erro retornado pela API
        """
        tamanho = min(tamanho, self.MAX_TAMANHO)
        payload = {"query": query, "pagina": pagina, "tamanho": tamanho}
        cache_key = self._build_cache_key("simples", payload)

        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit: {cache_key}")
            return cast(
                Dict[str, Any],
                json.loads(cached) if isinstance(cached, str) else cached,
            )

        data = await self._post(payload)
        result = self._normalize_response(data, pagina, tamanho)

        self.cache.set(cache_key, result, ttl=3600)
        return result

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
    ) -> Dict[str, Any]:
        """
        Busca decisões com filtros avançados.

        Cobre acórdãos e decisões monocráticas do TJDFT.

        Args:
            query: Termo de busca. Default "" (sem filtro de tema).
            relator: Nome exato do relator (ver GET /pesquisa → relatores).
            classe: Classe processual (ex: "APELAÇÃO CÍVEL").
            orgao_julgador: Órgão julgador (ex: "1ª TURMA CÍVEL").
            base: Base documental: "acordaos" ou "decisoes".
            subbase: Subbase: "acordaos", "acordaos-tr", "decisoes-monocraticas".
            revisor: Nome exato do revisor (campo: nomeRevisor).
            relator_designado: Nome do relator designado (campo: nomeRelatorDesignado).
            processo: Número CNJ do processo (ex: "0702180-36.2024.8.07.0001").
            pagina: Página (0-indexed). Default: 0.
            tamanho: Resultados por página. Máx: 40. Default: 20.

        Returns:
            Mesmo formato de buscar_simples.

        Raises:
            TJDFTConnectionError, TJDFTTimeoutError, TJDFTAPIError

        Note:
            Filtro por data (dataJulgamento/dataPublicacao) não é suportado
            — causa erro 500 na API.
        """
        tamanho = min(tamanho, self.MAX_TAMANHO)

        termos = []
        if relator:
            termos.append({"campo": "nomeRelator", "valor": relator})
        if classe:
            termos.append({"campo": "descricaoClasseCnj", "valor": classe})
        if orgao_julgador:
            termos.append({"campo": "descricaoOrgaoJulgador", "valor": orgao_julgador})
        if base:
            termos.append({"campo": "base", "valor": base})
        if subbase:
            termos.append({"campo": "subbase", "valor": subbase})
        if revisor:
            termos.append({"campo": "nomeRevisor", "valor": revisor})
        if relator_designado:
            termos.append({"campo": "nomeRelatorDesignado", "valor": relator_designado})
        if processo:
            termos.append({"campo": "processo", "valor": processo})

        payload: Dict[str, Any] = {"query": query, "pagina": pagina, "tamanho": tamanho}
        if termos:
            payload["termosAcessorios"] = termos

        cache_key = self._build_cache_key("filtrada", payload)

        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit: {cache_key}")
            return cast(
                Dict[str, Any],
                json.loads(cached) if isinstance(cached, str) else cached,
            )

        data = await self._post(payload)
        result = self._normalize_response(data, pagina, tamanho)

        self.cache.set(cache_key, result, ttl=3600)
        return result

    async def buscar_todas_paginas(
        self,
        query: str = "",
        max_paginas: int = 10,
        tamanho: int = 40,
        **filtros,
    ) -> List[Dict[str, Any]]:
        """
        Coleta acórdãos de múltiplas páginas automaticamente.

        Args:
            query: Termo de busca.
            max_paginas: Limite de páginas a buscar. Default: 10.
            tamanho: Resultados por página (máx 40). Default: 40.
            **filtros: Filtros aceitos por buscar_com_filtros
                       (relator, classe, orgao_julgador, base, etc.)

        Returns:
            Lista de todos os registros coletados.
        """
        all_registros: List[Dict[str, Any]] = []
        tamanho = min(tamanho, self.MAX_TAMANHO)

        logger.info(f"Iniciando busca multi-página: query='{query}', max={max_paginas}")

        for pagina in range(max_paginas):
            result = await self.buscar_com_filtros(
                query=query, pagina=pagina, tamanho=tamanho, **filtros
            )

            registros = result.get("registros", [])
            if not registros:
                logger.info(f"Sem mais resultados na página {pagina}")
                break

            all_registros.extend(registros)
            logger.info(
                "Página %s: %s registros (total: %s)",
                pagina,
                len(registros),
                len(all_registros),
            )

            total = result.get("total", 0)
            if len(all_registros) >= total:
                logger.info(f"Todos os {len(all_registros)} registros coletados")
                break

            await asyncio.sleep(0.1)

        logger.info(f"Busca concluída: {len(all_registros)} registros")
        return all_registros

    async def get_metadata(self) -> Dict[str, Any]:
        """
        Obtém listas de valores válidos para filtros.

        Returns:
            Dict com:
            - relatores: Lista de 228 nomes de relatores
            - revisores: Lista de 63 revisores
            - designados: Lista de 200 relatores designados
            - classes: Lista de 125 classes processuais
            - orgaos: Lista de 33 grupos de órgãos com variantes

        Raises:
            TJDFTConnectionError, TJDFTTimeoutError, TJDFTAPIError
        """
        cache_key = "tjdft:metadata"

        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug("Metadata cache hit")
            return cast(
                Dict[str, Any],
                json.loads(cached) if isinstance(cached, str) else cached,
            )

        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' statement.")

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await self.client.get(self.BASE_URL)
                response.raise_for_status()
                metadata = cast(Dict[str, Any], response.json())
                self.cache.set(cache_key, metadata, ttl=86400)
                return metadata

            except ConnectError as e:
                if attempt == self.MAX_RETRIES:
                    raise TJDFTConnectionError(f"Falha de conexão: {e}") from e
                await asyncio.sleep(2**attempt)

            except TimeoutException as e:
                if attempt == self.MAX_RETRIES:
                    raise TJDFTTimeoutError(f"Timeout: {e}") from e
                await asyncio.sleep(2**attempt)

            except HTTPStatusError as e:
                raise TJDFTAPIError(
                    f"Erro API {e.response.status_code}: {e.response.text}"
                ) from e

            except Exception as e:
                raise TJDFTClientError(f"Erro inesperado: {e}") from e

        raise TJDFTClientError("Falha ao obter metadados")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_cache_key(self, search_type: str, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        h = hashlib.md5(serialized.encode()).hexdigest()[:8]
        return f"tjdft:{search_type}:{h}"

    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST para o endpoint de busca com retry e backoff."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' statement.")

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.debug(
                    f"POST {self.BASE_URL} attempt={attempt} payload={payload}"
                )
                response = await self.client.post(self.BASE_URL, json=payload)
                response.raise_for_status()
                return cast(Dict[str, Any], response.json())

            except ConnectError as e:
                logger.warning(f"Conexão falhou (tentativa {attempt}): {e}")
                if attempt == self.MAX_RETRIES:
                    raise TJDFTConnectionError(
                        f"Falha de conexão após {self.MAX_RETRIES} tentativas"
                    ) from e
                await asyncio.sleep(2**attempt)

            except TimeoutException as e:
                logger.warning(f"Timeout (tentativa {attempt}): {e}")
                if attempt == self.MAX_RETRIES:
                    raise TJDFTTimeoutError(
                        f"Timeout após {self.MAX_RETRIES} tentativas"
                    ) from e
                await asyncio.sleep(2**attempt)

            except HTTPStatusError as e:
                logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
                if 400 <= e.response.status_code < 500:
                    raise TJDFTAPIError(
                        f"Erro {e.response.status_code}: {e.response.text}"
                    ) from e
                if attempt == self.MAX_RETRIES:
                    raise TJDFTAPIError(
                        "Erro servidor "
                        f"{e.response.status_code} após {self.MAX_RETRIES} tentativas"
                    ) from e
                await asyncio.sleep(2**attempt)

            except Exception as e:
                logger.error(f"Erro inesperado: {e}")
                raise TJDFTClientError(f"Erro inesperado: {e}") from e

        raise TJDFTClientError("Falha ao completar requisição")

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
