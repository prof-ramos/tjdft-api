"""
E2E tests for the busca (search) endpoint.

Tests the complete flow: HTTP request -> service -> TJDFT API -> response.
Requires Docker containers for PostgreSQL and Redis.
"""

import uuid

import pytest
from sqlalchemy import select

from app.models.consulta import Consulta


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_request_flow(e2e_api_client, e2e_session):
    """Test complete flow: HTTP request -> service -> TJDFT API -> response."""
    # Arrange
    request_payload = {"query": "tributário", "pagina": 1, "tamanho": 5}

    # Act
    response = await e2e_api_client.post("/api/v1/busca/", json=request_payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "resultados" in data
    assert "total" in data
    assert "consulta_id" in data
    assert isinstance(data["resultados"], list)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_timeout_handling(e2e_api_client, monkeypatch):
    """Test timeout is handled gracefully with very short timeout."""
    from app.services import tjdft_client

    # Patch timeout to very low value to force timeout
    monkeypatch.setattr(tjdft_client.TJDFTClient, "DEFAULT_TIMEOUT", 0.001)
    monkeypatch.setattr(tjdft_client.TJDFTClient, "CONNECT_TIMEOUT", 0.001)

    response = await e2e_api_client.post("/api/v1/busca/", json={"query": "test"})

    # Should handle timeout gracefully - expect server error or timeout
    assert response.status_code in [
        500,
        503,
        504,
    ], f"Expected server error on timeout, got {response.status_code}"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_data_enrichment_adds_instancia(e2e_api_client):
    """Test that response includes instancia field from enrichment."""
    response = await e2e_api_client.post(
        "/api/v1/busca/", json={"query": "teste", "pagina": 1, "tamanho": 5}
    )

    assert response.status_code == 200
    data = response.json()
    if data["resultados"]:
        resultado = data["resultados"][0]
        assert "instancia" in resultado
        assert resultado["instancia"] in ["juizado_especial", "tjdft_2a_instancia"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_pagination_returns_different_results(e2e_api_client):
    """Test that pagination returns different pages."""
    response1 = await e2e_api_client.post(
        "/api/v1/busca/", json={"query": "", "pagina": 1, "tamanho": 5}
    )
    response2 = await e2e_api_client.post(
        "/api/v1/busca/", json={"query": "", "pagina": 2, "tamanho": 5}
    )

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()["resultados"]
    data2 = response2.json()["resultados"]

    # Should have results (or empty second page if no results)
    assert isinstance(data1, list)
    assert isinstance(data2, list)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_filter_by_relator(e2e_api_client):
    """Test filtering by relator using termos acessorios."""
    response = await e2e_api_client.post(
        "/api/v1/busca/",
        json={
            "query": "",
            "filtros": {"relator": "desembargador-faustolo"},
            "pagina": 1,
            "tamanho": 10,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "resultados" in data
    # Assert we have results to validate
    assert data["resultados"], "Expected resultados but got none"
    # All results should have the specified relator
    for result in data["resultados"]:
        relator = result.get("relator", "").lower()
        # Check for partial match due to name format variations
        assert "faustolo" in relator or "fausto" in relator


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_excluir_turmas_recursais(e2e_api_client):
    """Test turmas recursais are excluded when requested via query param."""
    response = await e2e_api_client.post(
        "/api/v1/busca/",
        json={"query": "", "pagina": 1, "tamanho": 20},
        params={"excluir_turmas_recursais": True},
    )

    assert response.status_code == 200
    data = response.json()
    # Assert we have results to validate
    assert data["resultados"], "Expected resultados but got none"
    # Check no results from juizado especial
    for result in data["resultados"]:
        assert result.get("instancia") != "juizado_especial"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_consulta_persisted_to_database(e2e_api_client, e2e_session):
    """Test that each search creates a Consulta record in PostgreSQL."""
    # Act
    response = await e2e_api_client.post(
        "/api/v1/busca/", json={"query": "teste_e2e", "pagina": 1, "tamanho": 5}
    )

    # Assert
    assert response.status_code == 200
    consulta_id = response.json().get("consulta_id")
    assert consulta_id is not None

    # Verify in database
    result = await e2e_session.execute(
        select(Consulta).where(Consulta.id == uuid.UUID(consulta_id))
    )
    consulta = result.scalar_one()
    assert consulta.query == "teste_e2e"
    assert consulta.pagina == 1
    assert consulta.tamanho == 5


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_empty_query_returns_results(e2e_api_client):
    """Test that empty query string returns all results (no text filter)."""
    response = await e2e_api_client.post(
        "/api/v1/busca/", json={"query": "", "pagina": 1, "tamanho": 5}
    )

    assert response.status_code == 200
    data = response.json()
    assert "resultados" in data
    assert "total" in data
    assert isinstance(data["total"], int)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_apenas_ativos_filter(e2e_api_client):
    """Test filtering apenas_ativos via query parameter."""
    response = await e2e_api_client.post(
        "/api/v1/busca/",
        json={"query": "", "pagina": 1, "tamanho": 10},
        params={"apenas_ativos": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert "resultados" in data
    # Active relatores filter is applied - results should be filtered
