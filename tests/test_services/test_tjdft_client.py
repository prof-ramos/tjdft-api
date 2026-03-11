"""Tests for TJDFT API Client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.tjdft_client import (
    TJDFTAPIError,
    TJDFTClient,
    TJDFTConnectionError,
    TJDFTTimeoutError,
)
from app.utils.cache import CacheManager

pytestmark = pytest.mark.unit


@pytest.fixture
def cache_manager() -> CacheManager:
    """Create a cache manager for testing."""
    return CacheManager(default_ttl=3600)


@pytest.fixture
def mock_search_response() -> MagicMock:
    """Create a mock HTTP response for search endpoints."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "registros": [
            {
                "numero": "12345",
                "classe": "APELACAO CIVEL",
                "relator": "JOAO DA SILVA",
                "ementa": "Ementa teste",
            }
        ],
        "hits": {"value": 1},
        "agregacoes": {"classes": {"APELACAO CIVEL": 1}},
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_metadata_response() -> MagicMock:
    """Create a mock metadata response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "relatores": ["JOAO DA SILVA", "MARIA SANTOS"],
        "classes": ["APELACAO CIVEL", "AGRAVO DE INSTRUMENTO"],
        "orgaos": [
            {
                "base": "1A TURMA CIVEL",
                "agregador": False,
                "items": ["1A TURMA CIVEL"],
            }
        ],
    }
    response.raise_for_status = MagicMock()
    return response


class TestTJDFTClient:
    """Test suite for TJDFTClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, cache_manager: CacheManager) -> None:
        client = TJDFTClient(cache_manager)
        assert client.cache == cache_manager
        assert client.client is None

    @pytest.mark.asyncio
    async def test_async_context_manager(self, cache_manager: CacheManager) -> None:
        async with TJDFTClient(cache_manager) as client:
            assert client.client is not None

        assert client.client is None

    @pytest.mark.asyncio
    async def test_buscar_simples_success(
        self,
        cache_manager: CacheManager,
        mock_search_response: MagicMock,
    ) -> None:
        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = mock_search_response

                result = await client.buscar_simples("tributario")

                assert result["total"] == 1
                assert result["pagina"] == 0
                assert result["tamanho"] == 20
                assert len(result["registros"]) == 1
                assert result["agregacoes"]["classes"]["APELACAO CIVEL"] == 1

                mock_post.assert_called_once_with(
                    client.BASE_URL,
                    json={"query": "tributario", "pagina": 0, "tamanho": 20},
                )

    @pytest.mark.asyncio
    async def test_buscar_simples_accepts_empty_query(
        self,
        cache_manager: CacheManager,
        mock_search_response: MagicMock,
    ) -> None:
        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = mock_search_response

                await client.buscar_simples("")

                mock_post.assert_called_once_with(
                    client.BASE_URL,
                    json={"query": "", "pagina": 0, "tamanho": 20},
                )

    @pytest.mark.asyncio
    async def test_buscar_com_filtros(
        self,
        cache_manager: CacheManager,
        mock_search_response: MagicMock,
    ) -> None:
        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = mock_search_response

                result = await client.buscar_com_filtros(
                    query="tributario",
                    relator="JOAO DA SILVA",
                    classe="APELACAO CIVEL",
                    orgao_julgador="1A TURMA CIVEL",
                    base="acordaos",
                    subbase="acordaos",
                    processo="0702180-36.2024.8.07.0001",
                    pagina=2,
                    tamanho=50,
                )

                assert result["total"] == 1

                payload = mock_post.call_args.kwargs["json"]
                assert payload["query"] == "tributario"
                assert payload["pagina"] == 2
                assert payload["tamanho"] == 40
                assert payload["termosAcessorios"] == [
                    {"campo": "nomeRelator", "valor": "JOAO DA SILVA"},
                    {"campo": "descricaoClasseCnj", "valor": "APELACAO CIVEL"},
                    {"campo": "descricaoOrgaoJulgador", "valor": "1A TURMA CIVEL"},
                    {"campo": "base", "valor": "acordaos"},
                    {"campo": "subbase", "valor": "acordaos"},
                    {"campo": "processo", "valor": "0702180-36.2024.8.07.0001"},
                ]

    @pytest.mark.asyncio
    async def test_buscar_simples_caching(
        self,
        cache_manager: CacheManager,
        mock_search_response: MagicMock,
    ) -> None:
        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = mock_search_response

                result1 = await client.buscar_simples("tributario")
                result2 = await client.buscar_simples("tributario")

                assert mock_post.call_count == 1
                assert result1 == result2

    @pytest.mark.asyncio
    async def test_buscar_com_filtros_caching(
        self,
        cache_manager: CacheManager,
        mock_search_response: MagicMock,
    ) -> None:
        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = mock_search_response

                await client.buscar_com_filtros("query", relator="JOAO")
                await client.buscar_com_filtros("query", relator="JOAO")
                await client.buscar_com_filtros("query", relator="MARIA")

                assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_buscar_todas_paginas(
        self,
        cache_manager: CacheManager,
    ) -> None:
        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client, "buscar_com_filtros", new_callable=AsyncMock
            ) as mock_buscar:
                mock_buscar.side_effect = [
                    {
                        "registros": [{"numero": "1"}, {"numero": "2"}],
                        "total": 3,
                    },
                    {
                        "registros": [{"numero": "3"}],
                        "total": 3,
                    },
                ]

                with patch(
                    "app.services.tjdft_client.asyncio.sleep", new_callable=AsyncMock
                ):
                    results = await client.buscar_todas_paginas(
                        query="test", max_paginas=10
                    )

                assert len(results) == 3
                assert mock_buscar.call_count == 2

    @pytest.mark.asyncio
    async def test_buscar_todas_paginas_max_limit(
        self,
        cache_manager: CacheManager,
    ) -> None:
        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client, "buscar_com_filtros", new_callable=AsyncMock
            ) as mock_buscar:
                mock_buscar.return_value = {
                    "registros": [{"numero": "1"}],
                    "total": 10,
                }

                with patch(
                    "app.services.tjdft_client.asyncio.sleep", new_callable=AsyncMock
                ):
                    results = await client.buscar_todas_paginas(
                        query="test", max_paginas=3
                    )

                assert len(results) == 3
                assert mock_buscar.call_count == 3

    @pytest.mark.asyncio
    async def test_connection_error_retry(
        self,
        cache_manager: CacheManager,
        mock_search_response: MagicMock,
    ) -> None:
        from httpx import ConnectError

        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.side_effect = [
                    ConnectError("Connection failed"),
                    ConnectError("Connection failed"),
                    mock_search_response,
                ]

                with patch(
                    "app.services.tjdft_client.asyncio.sleep", new_callable=AsyncMock
                ):
                    result = await client.buscar_simples("test")

                assert result["total"] == 1
                assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_connection_error_max_retries(
        self,
        cache_manager: CacheManager,
    ) -> None:
        from httpx import ConnectError

        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.side_effect = ConnectError("Connection failed")

                with patch(
                    "app.services.tjdft_client.asyncio.sleep", new_callable=AsyncMock
                ):
                    with pytest.raises(
                        TJDFTConnectionError,
                        match="Falha de conexão após 3 tentativas",
                    ):
                        await client.buscar_simples("test")

                assert mock_post.call_count == client.MAX_RETRIES

    @pytest.mark.asyncio
    async def test_timeout_error(
        self,
        cache_manager: CacheManager,
    ) -> None:
        from httpx import TimeoutException

        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.side_effect = TimeoutException("Request timed out")

                with patch(
                    "app.services.tjdft_client.asyncio.sleep", new_callable=AsyncMock
                ):
                    with pytest.raises(
                        TJDFTTimeoutError,
                        match="Timeout após 3 tentativas",
                    ):
                        await client.buscar_simples("test")

    @pytest.mark.asyncio
    async def test_http_client_error_no_retry(
        self,
        cache_manager: CacheManager,
    ) -> None:
        from httpx import HTTPStatusError

        response = MagicMock()
        response.status_code = 400
        response.text = "Bad Request"

        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.side_effect = HTTPStatusError(
                    "Client error",
                    request=MagicMock(),
                    response=response,
                )

                with pytest.raises(TJDFTAPIError, match="Erro 400: Bad Request"):
                    await client.buscar_simples("test")

                assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_http_server_error_retry(
        self,
        cache_manager: CacheManager,
        mock_search_response: MagicMock,
    ) -> None:
        from httpx import HTTPStatusError

        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"

        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.side_effect = [
                    HTTPStatusError(
                        "Server error",
                        request=MagicMock(),
                        response=error_response,
                    ),
                    HTTPStatusError(
                        "Server error",
                        request=MagicMock(),
                        response=error_response,
                    ),
                    mock_search_response,
                ]

                with patch(
                    "app.services.tjdft_client.asyncio.sleep", new_callable=AsyncMock
                ):
                    result = await client.buscar_simples("test")

                assert result["total"] == 1
                assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_http_server_error_max_retries(
        self,
        cache_manager: CacheManager,
    ) -> None:
        from httpx import HTTPStatusError

        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"

        async with TJDFTClient(cache_manager) as client:
            with patch.object(
                client.client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.side_effect = HTTPStatusError(
                    "Server error",
                    request=MagicMock(),
                    response=error_response,
                )

                with patch(
                    "app.services.tjdft_client.asyncio.sleep", new_callable=AsyncMock
                ):
                    with pytest.raises(
                        TJDFTAPIError,
                        match="Erro servidor 500 após 3 tentativas",
                    ):
                        await client.buscar_simples("test")

                assert mock_post.call_count == client.MAX_RETRIES

    @pytest.mark.asyncio
    async def test_get_metadata(
        self,
        cache_manager: CacheManager,
        mock_metadata_response: MagicMock,
    ) -> None:
        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_metadata_response

                metadata = await client.get_metadata()

                assert "relatores" in metadata
                assert "classes" in metadata
                assert "orgaos" in metadata
                assert len(metadata["relatores"]) == 2

    @pytest.mark.asyncio
    async def test_get_metadata_caching(
        self,
        cache_manager: CacheManager,
        mock_metadata_response: MagicMock,
    ) -> None:
        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_metadata_response

                await client.get_metadata()
                await client.get_metadata()

                assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_build_cache_key(self, cache_manager: CacheManager) -> None:
        async with TJDFTClient(cache_manager) as client:
            params1 = {"query": "test", "pagina": 1}
            params2 = {"query": "test", "pagina": 1}
            params3 = {"query": "test", "pagina": 2}

            key1 = client._build_cache_key("simples", params1)
            key2 = client._build_cache_key("simples", params2)
            key3 = client._build_cache_key("simples", params3)

            assert key1 == key2
            assert key1 != key3
            assert "simples" in key1

    @pytest.mark.asyncio
    async def test_client_without_context_manager(
        self,
        cache_manager: CacheManager,
    ) -> None:
        client = TJDFTClient(cache_manager)

        with pytest.raises(RuntimeError, match="Client not initialized"):
            await client.buscar_simples("test")
