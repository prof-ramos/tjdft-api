"""
Tests for TJDFT API Client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.tjdft_client import (
    TJDFTClient,
    TJDFTClientError,
    TJDFTConnectionError,
    TJDFTTimeoutError,
    TJDFTAPIError,
)
from app.utils.cache import CacheManager


@pytest.fixture
def cache_manager():
    """Create a cache manager for testing."""
    return CacheManager(default_ttl=3600)


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "dados": [
            {
                "numero": "12345",
                "classe": "APELAÇÃO CÍVEL",
                "relator": "JOÃO DA SILVA",
                "ementa": "Ementa teste",
            }
        ],
        "paginacao": {
            "total": 1,
            "pagina": 1,
            "tamanho": 20,
        }
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_metadata_response():
    """Create a mock metadata response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "relatores": ["JOÃO DA SILVA", "MARIA SANTOS"],
        "classes": ["APELAÇÃO CÍVEL", "AGRAVO DE INSTRUMENTO"],
        "orgaos": [
            {
                "base": "1ª TURMA CÍVEL",
                "agregador": False,
                "items": ["1ª TURMA CÍVEL"]
            }
        ]
    }
    response.raise_for_status = MagicMock()
    return response


class TestTJDFTClient:
    """Test suite for TJDFTClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, cache_manager):
        """Test client initialization."""
        client = TJDFTClient(cache_manager)
        assert client.cache == cache_manager
        assert client.client is None

    @pytest.mark.asyncio
    async def test_async_context_manager(self, cache_manager):
        """Test async context manager."""
        async with TJDFTClient(cache_manager) as client:
            assert client.client is not None

        # Client should be closed after exiting context
        assert client.client is not None  # Reference still exists but connection is closed

    @pytest.mark.asyncio
    async def test_buscar_simples_success(self, cache_manager, mock_response):
        """Test simple search with successful response."""
        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response

                result = await client.buscar_simples("tributário")

                assert result["sucesso"] is True
                assert len(result["dados"]) == 1
                assert result["dados"][0]["numero"] == "12345"
                assert result["paginacao"]["total"] == 1

                # Verify request was made
                mock_get.assert_called_once()
                call_args = mock_get.call_args
                assert "q" in call_args.kwargs["params"]
                assert call_args.kwargs["params"]["q"] == "tributário"

    @pytest.mark.asyncio
    async def test_buscar_simples_empty_query(self, cache_manager):
        """Test simple search with empty query raises error."""
        async with TJDFTClient(cache_manager) as client:
            with pytest.raises(ValueError, match="Query parameter cannot be empty"):
                await client.buscar_simples("")

    @pytest.mark.asyncio
    async def test_buscar_simples_whitespace_query(self, cache_manager):
        """Test simple search with whitespace query raises error."""
        async with TJDFTClient(cache_manager) as client:
            with pytest.raises(ValueError, match="Query parameter cannot be empty"):
                await client.buscar_simples("   ")

    @pytest.mark.asyncio
    async def test_buscar_com_filtros(self, cache_manager, mock_response):
        """Test search with filters."""
        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response

                result = await client.buscar_com_filtros(
                    query="tributário",
                    relator="JOÃO DA SILVA",
                    classe="APELAÇÃO CÍVEL",
                    orgao_julgador="1ª TURMA CÍVEL",
                    data_inicio="2024-01-01",
                    data_fim="2024-12-31",
                    pagina=2,
                    tamanho=50
                )

                assert result["sucesso"] is True

                # Verify request parameters
                call_args = mock_get.call_args
                params = call_args.kwargs["params"]
                assert params["q"] == "tributário"
                assert params["relator"] == "JOÃO DA SILVA"
                assert params["classe"] == "APELAÇÃO CÍVEL"
                assert params["orgao_julgador"] == "1ª TURMA CÍVEL"
                assert params["data_inicio"] == "2024-01-01"
                assert params["data_fim"] == "2024-12-31"
                assert params["pagina"] == 2
                assert params["tamanho"] == 50

    @pytest.mark.asyncio
    async def test_buscar_simples_caching(self, cache_manager, mock_response):
        """Test that simple search results are cached."""
        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response

                # First call - should hit API
                result1 = await client.buscar_simples("tributário")
                assert mock_get.call_count == 1

                # Second call with same params - should use cache
                result2 = await client.buscar_simples("tributário")
                assert mock_get.call_count == 1  # No additional call

                # Results should be identical
                assert result1 == result2

    @pytest.mark.asyncio
    async def test_buscar_com_filtros_caching(self, cache_manager, mock_response):
        """Test that filtered search results are cached."""
        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response

                # First call
                await client.buscar_com_filtros("query", relator="JOÃO")
                assert mock_get.call_count == 1

                # Second call with same filters - should use cache
                await client.buscar_com_filtros("query", relator="JOÃO")
                assert mock_get.call_count == 1

                # Different filter - should make new request
                await client.buscar_com_filtros("query", relator="MARIA")
                assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_buscar_todas_paginas(self, cache_manager):
        """Test multi-page search."""
        # Mock responses for 3 pages
        responses = [
            MagicMock(
                status_code=200,
                json=lambda: {
                    "dados": [{"numero": f"{i}"} for i in range(20)],
                    "paginacao": {"total": 50, "pagina": 1, "tamanho": 20}
                },
                raise_for_status=MagicMock()
            ),
            MagicMock(
                status_code=200,
                json=lambda: {
                    "dados": [{"numero": f"{i}"} for i in range(20, 40)],
                    "paginacao": {"total": 50, "pagina": 2, "tamanho": 20}
                },
                raise_for_status=MagicMock()
            ),
            MagicMock(
                status_code=200,
                json=lambda: {
                    "dados": [{"numero": f"{i}"} for i in range(40, 50)],
                    "paginacao": {"total": 50, "pagina": 3, "tamanho": 20}
                },
                raise_for_status=MagicMock()
            ),
        ]

        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = responses

                results = await client.buscar_todas_paginas(
                    query="test",
                    max_paginas=10
                )

                assert len(results) == 50
                assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_buscar_todas_paginas_max_limit(self, cache_manager):
        """Test multi-page search respects max_pages limit."""
        # Mock 5 pages worth of data
        responses = [
            MagicMock(
                status_code=200,
                json=lambda page=page: {
                    "dados": [{"numero": f"{i}"} for i in range(20)],
                    "paginacao": {"total": 200, "pagina": page, "tamanho": 20}
                },
                raise_for_status=MagicMock()
            )
            for page in range(1, 6)
        ]

        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = responses

                results = await client.buscar_todas_paginas(
                    query="test",
                    max_paginas=3  # Only fetch 3 pages
                )

                # Should only fetch 3 pages (60 results)
                assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_connection_error_retry(self, cache_manager):
        """Test retry logic on connection errors."""
        from httpx import ConnectError

        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                # Fail first 2 times, succeed on 3rd
                mock_get.side_effect = [
                    ConnectError("Connection failed"),
                    ConnectError("Connection failed"),
                    MagicMock(
                        status_code=200,
                        json=lambda: {"dados": [], "paginacao": {}},
                        raise_for_status=MagicMock()
                    )
                ]

                result = await client.buscar_simples("test")
                assert result["sucesso"] is True
                assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_connection_error_max_retries(self, cache_manager):
        """Test that max retries is respected."""
        from httpx import ConnectError

        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = ConnectError("Connection failed")

                with pytest.raises(TJDFTConnectionError, match="Failed to connect after"):
                    await client.buscar_simples("test")

                # Should have tried MAX_RETRIES times
                assert mock_get.call_count == client.MAX_RETRIES

    @pytest.mark.asyncio
    async def test_timeout_error(self, cache_manager):
        """Test timeout error handling."""
        from httpx import TimeoutException

        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = TimeoutException("Request timed out")

                with pytest.raises(TJDFTTimeoutError, match="Request timed out after"):
                    await client.buscar_simples("test")

    @pytest.mark.asyncio
    async def test_http_client_error_no_retry(self, cache_manager):
        """Test that 4xx errors don't trigger retries."""
        from httpx import HTTPStatusError

        response = MagicMock()
        response.status_code = 400
        response.text = "Bad Request"

        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                http_error = HTTPStatusError(
                    "Client error",
                    request=MagicMock(),
                    response=response
                )
                mock_get.side_effect = http_error

                with pytest.raises(TJDFTAPIError, match="API client error"):
                    await client.buscar_simples("test")

                # Should not retry 4xx errors
                assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_http_server_error_retry(self, cache_manager):
        """Test that 5xx errors trigger retries."""
        from httpx import HTTPStatusError

        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"dados": [], "paginacao": {}}
        success_response.raise_for_status = MagicMock()

        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                http_error = HTTPStatusError(
                    "Server error",
                    request=MagicMock(),
                    response=error_response
                )

                mock_get.side_effect = [
                    http_error,
                    http_error,
                    success_response
                ]

                result = await client.buscar_simples("test")
                assert result["sucesso"] is True
                assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_get_metadata(self, cache_manager, mock_metadata_response):
        """Test metadata retrieval."""
        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_metadata_response

                metadata = await client.get_metadata()

                assert "relatores" in metadata
                assert "classes" in metadata
                assert "orgaos" in metadata
                assert len(metadata["relatores"]) == 2
                assert "JOÃO DA SILVA" in metadata["relatores"]

    @pytest.mark.asyncio
    async def test_get_metadata_caching(self, cache_manager, mock_metadata_response):
        """Test that metadata is cached."""
        async with TJDFTClient(cache_manager) as client:
            with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_metadata_response

                # First call
                await client.get_metadata()
                assert mock_get.call_count == 1

                # Second call - should use cache (24h TTL)
                await client.get_metadata()
                assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_extract_results_from_list(self, cache_manager):
        """Test _extract_results with list response."""
        async with TJDFTClient(cache_manager) as client:
            data = [{"id": 1}, {"id": 2}]
            results = client._extract_results(data)
            assert results == data

    @pytest.mark.asyncio
    async def test_extract_results_from_dict(self, cache_manager):
        """Test _extract_results with dict response."""
        async with TJDFTClient(cache_manager) as client:
            data = {
                "dados": [{"id": 1}, {"id": 2}]
            }
            results = client._extract_results(data)
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_extract_results_unknown_format(self, cache_manager):
        """Test _extract_results with unknown format."""
        async with TJDFTClient(cache_manager) as client:
            data = {"invalid": "format"}
            results = client._extract_results(data)
            assert results == []

    @pytest.mark.asyncio
    async def test_extract_pagination(self, cache_manager):
        """Test _extract_pagination."""
        async with TJDFTClient(cache_manager) as client:
            data = {
                "paginacao": {
                    "total": 100,
                    "pagina": 1,
                    "tamanho": 20
                }
            }
            params = {"pagina": 1, "tamanho": 20}

            paginacao = client._extract_pagination(data, params)

            assert paginacao["total"] == 100
            assert paginacao["pagina"] == 1
            assert paginacao["tamanho"] == 20

    @pytest.mark.asyncio
    async def test_build_cache_key(self, cache_manager):
        """Test cache key generation."""
        async with TJDFTClient(cache_manager) as client:
            params1 = {"q": "test", "pagina": 1}
            params2 = {"q": "test", "pagina": 1}
            params3 = {"q": "test", "pagina": 2}

            key1 = client._build_cache_key("simples", params1)
            key2 = client._build_cache_key("simples", params2)
            key3 = client._build_cache_key("simples", params3)

            # Same params should generate same key
            assert key1 == key2

            # Different params should generate different key
            assert key1 != key3

            # Key should contain search type
            assert "simples" in key1

    @pytest.mark.asyncio
    async def test_client_without_context_manager(self, cache_manager):
        """Test that using client without context manager raises error."""
        client = TJDFTClient(cache_manager)

        with pytest.raises(RuntimeError, match="Client not initialized"):
            await client.buscar_simples("test")
