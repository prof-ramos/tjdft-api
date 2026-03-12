"""Test Pydantic schemas for decisao operations."""

import pytest
from datetime import date, datetime
from pydantic import ValidationError

from app.schemas.decisao import (
    DecisaoBase,
    DecisaoCreate,
    DecisaoEnriquecida,
    DecisaoListResponse,
    DecisaoResponse,
    DecisaoUpdate,
)


class TestDecisaoBase:
    """Test DecisaoBase schema validation."""

    def test_valid_decisao_base_with_all_fields(self):
        """Should create valid DecisaoBase with all fields."""
        data = {
            "uuid": "12345678-1234-1234-1234-123456789012",
            "numeroProcesso": "0701234-56.2025.8.07.0016",
            "ementa": "Ementa do acórdão",
            "inteiroTeorHtml": "<p>Texto completo</p>",
            "nomeRelator": "Desembargador Fulano",
            "dataJulgamento": "2025-03-10",
            "dataPublicacao": "2025-03-15",
            "descricaoOrgaoJulgador": "6ª Câmara Cível",
            "descricaoClasseCnj": "Apelação Cível",
        }
        schema = DecisaoBase(**data)
        assert schema.uuid_tjdft == "12345678-1234-1234-1234-123456789012"
        assert schema.processo == "0701234-56.2025.8.07.0016"
        assert schema.ementa == "Ementa do acórdão"
        assert schema.relator == "Desembargador Fulano"
        assert schema.data_julgamento == date(2025, 3, 10)
        assert schema.orgao_julgador == "6ª Câmara Cível"
        assert schema.classe == "Apelação Cível"

    def test_decisao_base_all_fields_optional(self):
        """Should create DecisaoBase with all fields optional."""
        schema = DecisaoBase()
        assert schema.uuid_tjdft is None
        assert schema.processo is None
        assert schema.ementa is None
        assert schema.inteiro_teor is None
        assert schema.relator is None
        assert schema.data_julgamento is None
        assert schema.data_publicacao is None
        assert schema.orgao_julgador is None
        assert schema.classe is None

    def test_alias_mapping(self):
        """Should correctly map API field names to Python names."""
        data = {
            "uuid": "uuid-123",
            "numeroProcesso": "processo-123",
            "nomeRelator": "Relator Nome",
            "dataJulgamento": "2025-03-10",
            "dataPublicacao": "2025-03-15",
            "descricaoOrgaoJulgador": "Órgão Julgador",
            "descricaoClasseCnj": "Classe CNJ",
        }
        schema = DecisaoBase(**data)
        assert schema.uuid_tjdft == "uuid-123"
        assert schema.processo == "processo-123"
        assert schema.relator == "Relator Nome"
        assert schema.orgao_julgador == "Órgão Julgador"
        assert schema.classe == "Classe CNJ"

    def test_date_parse_iso_format(self):
        """Should parse ISO format datetime string."""
        schema = DecisaoBase(data_julgamento="2025-03-10T15:30:00Z")
        assert schema.data_julgamento == date(2025, 3, 10)

    def test_date_parse_date_string(self):
        """Should parse ISO date string."""
        schema = DecisaoBase(data_julgamento="2025-03-10")
        assert schema.data_julgamento == date(2025, 3, 10)

    def test_date_parse_invalid_string_returns_none(self):
        """Should return None for invalid date string."""
        schema = DecisaoBase(data_julgamento="invalid-date")
        assert schema.data_julgamento is None


class TestDecisaoUpdate:
    """Test DecisaoUpdate schema validation."""

    def test_all_fields_optional(self):
        """Should accept empty DecisaoUpdate."""
        schema = DecisaoUpdate()
        assert schema.processo is None
        assert schema.ementa is None
        assert schema.inteiro_teor is None
        assert schema.relator is None
        assert schema.data_julgamento is None
        assert schema.data_publicacao is None
        assert schema.orgao_julgador is None
        assert schema.classe is None

    def test_update_with_partial_data(self):
        """Should accept partial updates."""
        schema = DecisaoUpdate(ementa="Nova ementa")
        assert schema.ementa == "Nova ementa"
        assert schema.processo is None
        assert schema.relator is None

    def test_update_with_all_fields(self):
        """Should accept updates with all fields."""
        data = {
            "processo": "0701234-56.2025.8.07.0016",
            "ementa": "Ementa atualizada",
            "inteiro_teor": "Texto atualizado",
            "relator": "Novo Relator",
            "data_julgamento": "2025-03-11",
            "data_publicacao": "2025-03-16",
            "orgao_julgador": "3ª Turma Cível",
            "classe": "Procedimento",
        }
        schema = DecisaoUpdate(**data)
        assert schema.processo == "0701234-56.2025.8.07.0016"


class TestDecisaoEnriquecida:
    """Test DecisaoEnriquecida schema."""

    def test_enriched_fields(self):
        """Should accept enriched fields."""
        data = {
            "uuid": "uuid-123",
            "resumo_relevancia": {"categoria": "test"},
            "instancia": "tjdft_2a_instancia",
            "relatorAtivo": True,
        }
        schema = DecisaoEnriquecida(**data)
        assert schema.resumo_relevancia == {"categoria": "test"}
        assert schema.instancia == "tjdft_2a_instancia"
        assert schema.relator_ativo is True

    def test_inherits_from_base(self):
        """Should inherit fields from DecisaoBase."""
        data = {
            "uuid": "uuid-123",
            "numeroProcesso": "processo-123",
            "nomeRelator": "Relator",
        }
        schema = DecisaoEnriquecida(**data)
        assert schema.uuid_tjdft == "uuid-123"
        assert schema.processo == "processo-123"
        assert schema.relator == "Relator"


class TestDecisaoResponse:
    """Test DecisaoResponse schema."""

    def test_requires_id(self):
        """Should require id field."""
        with pytest.raises(ValidationError) as exc_info:
            DecisaoResponse()
        assert "id" in str(exc_info.value).lower()

    def test_requires_criado_em(self):
        """Should require criado_em field."""
        with pytest.raises(ValidationError) as exc_info:
            DecisaoResponse(id="123")
        assert "criado_em" in str(exc_info.value).lower()

    def test_valid_response(self):
        """Should create valid response."""
        schema = DecisaoResponse(
            id="123",
            criado_em=datetime(2025, 3, 10, 15, 30, 0),
        )
        assert schema.id == "123"
        assert schema.criado_em == datetime(2025, 3, 10, 15, 30, 0)


class TestDecisaoListResponse:
    """Test DecisaoListResponse schema."""

    def test_requires_all_fields(self):
        """Should require all fields."""
        with pytest.raises(ValidationError) as exc_info:
            DecisaoListResponse(
                items=[],
                total=10,
                pagina=1,
                tamanho=20,
            )
        assert "total_paginas" in str(exc_info.value).lower()

    def test_valid_list_response(self):
        """Should create valid list response."""
        items = [
            DecisaoResponse(
                id="1",
                criado_em=datetime(2025, 3, 10, 15, 30, 0),
            )
        ]
        schema = DecisaoListResponse(
            items=items,
            total=1,
            pagina=1,
            tamanho=20,
            total_paginas=1,
        )
        assert len(schema.items) == 1
        assert schema.total == 1
