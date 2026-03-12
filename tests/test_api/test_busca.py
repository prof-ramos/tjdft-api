"""Testes para endpoint de busca de decisões."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import HTTPStatusError, Response

from app.api.v1.endpoints.busca import router
from app.main import app
from app.schemas.decisao import DecisaoEnriquecida

pytestmark = pytest.mark.api


class TestBuscaRouter:
    """Testes para o router de busca."""

    def test_router_exists(self):
        """Verifica que o router de busca existe e tem os atributos esperados."""
        assert router is not None
        assert router.prefix == "/busca"
        assert router.tags == ["Busca"]

    def test_router_has_search_endpoint(self):
        """Verifica que o router possui o endpoint de busca."""
        # Verifica se há rotas registradas no router
        routes = [route for route in router.routes]
        assert len(routes) > 0, "Router should have at least one route"

        # Verifica se existe uma rota POST para o path raiz "/"
        post_routes = [
            route
            for route in routes
            if hasattr(route, "methods") and "POST" in route.methods
        ]
        assert len(post_routes) > 0, "Router should have a POST route"

    def test_router_import(self):
        """Verifica que o módulo do endpoint pode ser importado."""
        # Este teste serve como smoke test para garantir que não há
        # erros de importação circular ou dependências faltantes
        from app.api.v1.endpoints import busca

        assert hasattr(busca, "router")
        assert hasattr(busca, "buscar_decisoes")

    def test_endpoint_signature(self):
        """Verifica a assinatura do endpoint principal."""
        routes = [route for route in router.routes]
        post_route = None

        for route in routes:
            if (
                hasattr(route, "methods")
                and "POST" in route.methods
                and hasattr(route, "path")
            ):
                if route.path == "/busca/":
                    post_route = route
                    break

        assert post_route is not None, "POST /busca/ route should exist"
        assert post_route.path == "/busca/"
        assert "POST" in post_route.methods

    def test_app_exposes_versioned_busca_route(self):
        """Verifica que a aplicação expõe o endpoint versionado."""
        routes = [
            route
            for route in app.routes
            if hasattr(route, "methods") and "POST" in route.methods
        ]
        paths = {route.path for route in routes}

        assert "/api/v1/busca/" in paths


class TestBuscaHTTPResponses:
    """Test HTTP responses for /busca endpoint."""

    @pytest.mark.asyncio
    async def test_200_ok_successful_search(self, api_client):
        """200 OK - Busca bem-sucedida retorna resultados."""
        decisao = DecisaoEnriquecida(
            uuid="uuid-123",  # Usa alias "uuid" que serializa como "uuid"
            processo="0701234-56.2025.8.07.0016",
            ementa="Ementa teste",
            relator="Desembargador Teste",
            data_julgamento="2025-03-10",
            orgao_julgador="6ª Câmara Cível",
            classe="Apelação Cível",
        )

        response_data = {
            "resultados": [decisao],
            "total": 1,
            "total_filtrado": 1,
            "pagina": 1,
            "tamanho": 20,
            "consulta_id": "consulta-123",
        }

        with patch("app.api.v1.endpoints.busca.BuscaService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.buscar.return_value = response_data
            mock_service_cls.return_value = mock_service

            response = await api_client.post(
                "/api/v1/busca/",
                json={"query": "tributário"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["total_filtrado"] == 1
        assert len(data["resultados"]) == 1
        # Pydantic serializa usando alias "uuid"
        assert data["resultados"][0]["uuid"] == "uuid-123"

    @pytest.mark.asyncio
    async def test_422_empty_query(self, api_client):
        """422 Unprocessable Entity - Query vazia é rejeitada."""
        response = await api_client.post(
            "/api/v1/busca/",
            json={"query": ""},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("query" in str(err).lower() for err in data["detail"])

    @pytest.mark.asyncio
    async def test_422_missing_query_field(self, api_client):
        """422 Unprocessable Entity - Campo query ausente."""
        response = await api_client.post(
            "/api/v1/busca/",
            json={},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("query" in str(err).lower() for err in data["detail"])

    @pytest.mark.asyncio
    async def test_422_pagina_out_of_range_zero(self, api_client):
        """422 Unprocessable Entity - Pagina=0 é rejeitado."""
        response = await api_client.post(
            "/api/v1/busca/",
            json={"query": "teste", "pagina": 0},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("pagina" in str(err).lower() for err in data["detail"])

    @pytest.mark.asyncio
    async def test_422_pagina_out_of_range_negative(self, api_client):
        """422 Unprocessable Entity - Pagina negativa é rejeitada."""
        response = await api_client.post(
            "/api/v1/busca/",
            json={"query": "teste", "pagina": -1},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_422_tamanho_below_minimum(self, api_client):
        """422 Unprocessable Entity - Tamanho=0 é rejeitado."""
        response = await api_client.post(
            "/api/v1/busca/",
            json={"query": "teste", "tamanho": 0},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("tamanho" in str(err).lower() for err in data["detail"])

    @pytest.mark.asyncio
    async def test_422_tamanho_above_maximum(self, api_client):
        """422 Unprocessable Entity - Tamanho>100 é rejeitado."""
        response = await api_client.post(
            "/api/v1/busca/",
            json={"query": "teste", "tamanho": 101},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("tamanho" in str(err).lower() for err in data["detail"])

    @pytest.mark.asyncio
    async def test_422_invalid_filter_type(self, api_client):
        """422 Unprocessable Entity - Filtros com tipo inválido é rejeitado."""
        response = await api_client.post(
            "/api/v1/busca/",
            json={"query": "teste", "filtros": "not-a-dict"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_200_with_optional_fields(self, api_client):
        """200 OK - Busca com campos opcionais fornecidos."""
        response_data = {
            "resultados": [],
            "total": 0,
            "total_filtrado": 0,
            "pagina": 2,
            "tamanho": 50,
            "consulta_id": "consulta-456",
            "densidade": {"categoria": "escasso"},
        }

        with patch("app.api.v1.endpoints.busca.BuscaService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.buscar.return_value = response_data
            mock_service_cls.return_value = mock_service

            response = await api_client.post(
                "/api/v1/busca/",
                json={
                    "query": "tributário",
                    "pagina": 2,
                    "tamanho": 50,
                    "filtros": {"classe": "Apelação Cível"},
                    "excluir_turmas_recursais": True,
                    "apenas_ativos": True,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["pagina"] == 2
        assert data["tamanho"] == 50
        assert data["densidade"] == {"categoria": "escasso"}

    @pytest.mark.asyncio
    async def test_200_with_query_params_override(self, api_client):
        """200 OK - Query parameters sobrescrevem body."""
        response_data = {
            "resultados": [],
            "total": 0,
            "total_filtrado": 0,
            "pagina": 1,
            "tamanho": 20,
            "consulta_id": "consulta-789",
        }

        with patch("app.api.v1.endpoints.busca.BuscaService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.buscar.return_value = response_data
            mock_service_cls.return_value = mock_service

            # Body tem excluir_turmas_recursais=False, query param tem True
            response = await api_client.post(
                "/api/v1/busca/?excluir_turmas_recursais=true&apenas_ativos=true",
                json={"query": "teste", "excluir_turmas_recursais": False},
            )

        assert response.status_code == 200
        # Verifica que o service foi chamado com valores sobrescritos
        mock_service.buscar.assert_called_once()
        call_args = mock_service.buscar.call_args
        request_obj = call_args[0][0]
        assert request_obj.excluir_turmas_recursais is True
        assert request_obj.apenas_ativos is True

    @pytest.mark.asyncio
    async def test_500_tjdft_service_error(self, api_client):
        """500 Internal Server Error - Erro do serviço TJDFT."""
        from starlette.exceptions import HTTPException

        with patch(
            "app.api.v1.endpoints.busca.BuscaService",
        ) as mock_service_cls:
            mock_service = AsyncMock()
            # Usar HTTPException para que o FastAPI retorne o status code correto
            mock_service.buscar.side_effect = HTTPException(
                status_code=503, detail="TJDFT API unavailable"
            )
            mock_service_cls.return_value = mock_service

            response = await api_client.post(
                "/api/v1/busca/",
                json={"query": "tributário"},
            )

        # HTTPException é capturada pelo FastAPI e retorna o status code
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
