"""Test Pydantic schemas for consulta operations."""

import pytest
from pydantic import ValidationError

from app.schemas.consulta import (
    BuscaRequest,
    BuscaResponseEnriquecida,
    ConsultaResponse,
    DecisaoResponse,
)


class TestBuscaRequest:
    """Test BuscaRequest schema validation."""

    def test_requires_query(self):
        """Query field is required."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaRequest()
        assert "query" in str(exc_info.value).lower()

    def test_query_min_length_validation(self):
        """Query must have min_length=1."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaRequest(query="")
        assert "at least 1 character" in str(exc_info.value).lower()

    def test_default_pagina(self):
        """Pagina defaults to 1."""
        schema = BuscaRequest(query="test")
        assert schema.pagina == 1

    def test_pagina_minimum(self):
        """Pagina must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaRequest(query="test", pagina=0)
        assert "greater than or equal to 1" in str(exc_info.value).lower()

    def test_tamanho_defaults_to_20(self):
        """Tamanho defaults to 20."""
        schema = BuscaRequest(query="test")
        assert schema.tamanho == 20

    def test_tamanho_minimum(self):
        """Tamanho must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaRequest(query="test", tamanho=0)
        assert "greater than or equal to 1" in str(exc_info.value).lower()

    def test_tamanho_maximum(self):
        """Tamanho must be <= 100."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaRequest(query="test", tamanho=101)
        assert "less than or equal to 100" in str(exc_info.value).lower()

    def test_filtros_optional(self):
        """Filtros field is optional."""
        schema = BuscaRequest(query="test")
        assert schema.filtros is None

    def test_filtros_accepts_dict(self):
        """Filtros accepts dictionary."""
        filtros = {"relator": "desembargador-fulano"}
        schema = BuscaRequest(query="test", filtros=filtros)
        assert schema.filtros == filtros

    def test_excluir_turmas_recursais_optional(self):
        """excluir_turmas_recursais is optional."""
        schema = BuscaRequest(query="test")
        assert schema.excluir_turmas_recursais is None

    def test_excluir_turmas_recursais_accepts_bool(self):
        """excluir_turmas_recursais accepts bool."""
        schema = BuscaRequest(query="test", excluir_turmas_recursais=True)
        assert schema.excluir_turmas_recursais is True

    def test_apenas_ativos_optional(self):
        """apenas_ativos is optional."""
        schema = BuscaRequest(query="test")
        assert schema.apenas_ativos is None

    def test_apenas_ativos_accepts_bool(self):
        """apenas_ativos accepts bool."""
        schema = BuscaRequest(query="test", apenas_ativos=False)
        assert schema.apenas_ativos is False

    def test_full_valid_request(self):
        """Should accept valid request with all fields."""
        schema = BuscaRequest(
            query="tributário",
            pagina=2,
            tamanho=50,
            filtros={"classe": "Apelação Cível"},
            excluir_turmas_recursais=True,
            apenas_ativos=True,
        )
        assert schema.query == "tributário"
        assert schema.pagina == 2
        assert schema.tamanho == 50
        assert schema.excluir_turmas_recursais is True
        assert schema.apenas_ativos is True


class TestBuscaResponseEnriquecida:
    """Test BuscaResponseEnriquecida schema."""

    def test_requires_resultados(self):
        """resultados field is required."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaResponseEnriquecida(
                total=0,
                total_filtrado=0,
                pagina=1,
                tamanho=20,
                consulta_id="abc",
            )
        assert "resultados" in str(exc_info.value).lower()

    def test_requires_total(self):
        """total field is required."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaResponseEnriquecida(
                resultados=[],
                total_filtrado=0,
                pagina=1,
                tamanho=20,
                consulta_id="abc",
            )
        assert "total" in str(exc_info.value).lower()

    def test_requires_total_filtrado(self):
        """total_filtrado field is required."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaResponseEnriquecida(
                resultados=[],
                total=0,
                pagina=1,
                tamanho=20,
                consulta_id="abc",
            )
        assert "total_filtrado" in str(exc_info.value).lower()

    def test_requires_pagina(self):
        """pagina field is required."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaResponseEnriquecida(
                resultados=[],
                total=0,
                total_filtrado=0,
                tamanho=20,
                consulta_id="abc",
            )
        assert "pagina" in str(exc_info.value).lower()

    def test_requires_tamanho(self):
        """tamanho field is required."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaResponseEnriquecida(
                resultados=[],
                total=0,
                total_filtrado=0,
                pagina=1,
                consulta_id="abc",
            )
        assert "tamanho" in str(exc_info.value).lower()

    def test_requires_consulta_id(self):
        """consulta_id field is required."""
        with pytest.raises(ValidationError) as exc_info:
            BuscaResponseEnriquecida(
                resultados=[],
                total=0,
                total_filtrado=0,
                pagina=1,
                tamanho=20,
            )
        assert "consulta_id" in str(exc_info.value).lower()

    def test_densidade_optional(self):
        """densidade field is optional."""
        schema = BuscaResponseEnriquecida(
            resultados=[],
            total=0,
            total_filtrado=0,
            pagina=1,
            tamanho=20,
            consulta_id="abc",
        )
        assert schema.densidade is None

    def test_valid_response(self):
        """Should create valid enriched response."""
        decisao = DecisaoResponse(
            uuid_tjdft="uuid-123",
        )
        schema = BuscaResponseEnriquecida(
            resultados=[decisao],
            total=1,
            total_filtrado=1,
            pagina=1,
            tamanho=20,
            consulta_id="consulta-123",
            densidade={"categoria": "moderado"},
        )
        assert len(schema.resultados) == 1
        assert schema.total == 1
        assert schema.densidade == {"categoria": "moderado"}


class TestConsultaResponse:
    """Test ConsultaResponse schema."""

    def test_requires_id(self):
        """id field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ConsultaResponse(
                query="test",
                resultados_encontrados=0,
                pagina=1,
                tamanho=20,
                criado_em="2025-03-10T15:30:00",
            )
        assert "id" in str(exc_info.value).lower()

    def test_requires_query(self):
        """query field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ConsultaResponse(
                id="abc",
                resultados_encontrados=0,
                pagina=1,
                tamanho=20,
                criado_em="2025-03-10T15:30:00",
            )
        assert "query" in str(exc_info.value).lower()

    def test_requires_resultados_encontrados(self):
        """resultados_encontrados field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ConsultaResponse(
                id="abc",
                query="test",
                pagina=1,
                tamanho=20,
                criado_em="2025-03-10T15:30:00",
            )
        assert "resultados_encontrados" in str(exc_info.value).lower()

    def test_valid_consulta_response(self):
        """Should create valid consulta response."""
        schema = ConsultaResponse(
            id="uuid-123",
            query="tributário",
            filtros=None,
            resultados_encontrados=5,
            pagina=1,
            tamanho=20,
            criado_em="2025-03-10T15:30:00",
        )
        assert schema.id == "uuid-123"
        assert schema.query == "tributário"
        assert schema.resultados_encontrados == 5
