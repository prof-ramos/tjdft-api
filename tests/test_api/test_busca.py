"""Testes para endpoint de busca de decisões."""

import pytest

from app.api.v1.endpoints.busca import router
from app.main import app

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
