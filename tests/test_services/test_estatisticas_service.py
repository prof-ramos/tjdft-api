"""Tests for EstatisticasService."""

from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decisao import Decisao
from app.services.estatisticas_service import EstatisticasService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_analise_por_relator_no_decisoes(db_session: AsyncSession):
    """Test analysis when no decisions exist for relator."""
    service = EstatisticasService(db_session)

    result = await service.analise_por_relator("Relator Inexistente")

    assert result["relator"] == "Relator Inexistente"
    assert result["total_decisoes"] == 0
    assert result["orgaos"] == {}
    assert result["classes"] == {}
    assert result["temas_recorrentes"] == []
    assert result["media_por_mes"] == 0.0
    assert result["periodo_analisado"] == {}


@pytest.mark.asyncio
async def test_analise_por_relator_with_decisoes(db_session: AsyncSession):
    """Test analysis with existing decisions."""
    service = EstatisticasService(db_session)

    # Create test decisions
    decisao1 = Decisao(
        uuid_tjdft="test-uuid-1",
        relator="João Silva",
        orgao_julgador="Turma Cível",
        classe="Apelação",
        data_julgamento=date(2024, 1, 15),
        ementa="Direito civil e processual civil. Apelação conhecida.",
    )
    decisao2 = Decisao(
        uuid_tjdft="test-uuid-2",
        relator="João Silva",
        orgao_julgador="Turma Cível",
        classe="Agravo",
        data_julgamento=date(2024, 2, 20),
        ementa="Direito tributário. Agravo provido.",
    )
    db_session.add_all([decisao1, decisao2])
    await db_session.flush()

    result = await service.analise_por_relator("João Silva")

    assert result["relator"] == "João Silva"
    assert result["total_decisoes"] == 2
    assert result["orgaos"]["Turma Cível"] == 2
    assert result["classes"]["Apelação"] == 1
    assert result["classes"]["Agravo"] == 1
    assert result["media_por_mes"] > 0
    assert "inicio" in result["periodo_analisado"]
    assert "fim" in result["periodo_analisado"]


@pytest.mark.asyncio
async def test_analise_por_relator_com_periodo(db_session: AsyncSession):
    """Test analysis with date range filter."""
    service = EstatisticasService(db_session)

    # Create test decisions
    decisao1 = Decisao(
        uuid_tjdft="test-uuid-3",
        relator="Maria Santos",
        orgao_julgador="Turma Cível",
        data_julgamento=date(2024, 1, 15),
    )
    decisao2 = Decisao(
        uuid_tjdft="test-uuid-4",
        relator="Maria Santos",
        orgao_julgador="Turma Cível",
        data_julgamento=date(2024, 3, 20),
    )
    db_session.add_all([decisao1, decisao2])
    await db_session.flush()

    # Search only in January
    result = await service.analise_por_relator(
        "Maria Santos",
        data_inicio=date(2024, 1, 1),
        data_fim=date(2024, 1, 31),
    )

    assert result["total_decisoes"] == 1


@pytest.mark.asyncio
async def test_analise_por_tema_no_decisoes(db_session: AsyncSession):
    """Test theme analysis when no decisions match."""
    service = EstatisticasService(db_session)

    result = await service.analise_por_tema("Tema Inexistente")

    assert result["tema"] == "Tema Inexistente"
    assert result["total_decisoes"] == 0
    assert result["relatores"] == {}
    assert result["orgaos"] == {}
    assert result["evolucao_temporal"] == []
    assert result["decisoes_principais"] == []


@pytest.mark.asyncio
async def test_analise_por_tema_with_decisoes(db_session: AsyncSession):
    """Test theme analysis with matching decisions."""
    service = EstatisticasService(db_session)

    # Create test decisions
    decisao1 = Decisao(
        uuid_tjdft="test-uuid-5",
        relator="João Silva",
        orgao_julgador="Turma Cível",
        data_julgamento=date(2024, 1, 15),
        ementa="Tributário. ICMS. Base de cálculo.",
    )
    decisao2 = Decisao(
        uuid_tjdft="test-uuid-6",
        relator="Maria Santos",
        orgao_julgador="Turma Cível",
        data_julgamento=date(2024, 2, 20),
        ementa="Direito tributário. Taxa. Emolumentos.",
    )
    db_session.add_all([decisao1, decisao2])
    await db_session.flush()

    result = await service.analise_por_tema("tributário")

    assert result["tema"] == "tributário"
    assert result["total_decisoes"] == 2
    assert len(result["relatores"]) == 2
    assert len(result["evolucao_temporal"]) > 0
    assert len(result["decisoes_principais"]) == 2


@pytest.mark.asyncio
async def test_analise_temporal_no_decisoes(db_session: AsyncSession):
    """Test temporal analysis when no decisions exist."""
    service = EstatisticasService(db_session)

    result = await service.analise_temporal(
        date(2024, 1, 1),
        date(2024, 12, 31),
    )

    assert result["periodo"]["inicio"] == date(2024, 1, 1)
    assert result["periodo"]["fim"] == date(2024, 12, 31)
    assert result["total_decisoes"] == 0
    assert result["serie_temporal"] == []
    assert result["tendencia"] == "estavel"
    assert result["pico"] == {}
    assert result["media_por_periodo"] == 0.0


@pytest.mark.asyncio
async def test_analise_temporal_with_decisoes(db_session: AsyncSession):
    """Test temporal analysis with decisions."""
    service = EstatisticasService(db_session)

    # Create test decisions
    decisao1 = Decisao(
        uuid_tjdft="test-uuid-7",
        data_julgamento=date(2024, 1, 15),
    )
    decisao2 = Decisao(
        uuid_tjdft="test-uuid-8",
        data_julgamento=date(2024, 2, 20),
    )
    decisao3 = Decisao(
        uuid_tjdft="test-uuid-9",
        data_julgamento=date(2024, 3, 10),
    )
    db_session.add_all([decisao1, decisao2, decisao3])
    await db_session.flush()

    result = await service.analise_temporal(
        date(2024, 1, 1),
        date(2024, 12, 31),
        agrupamento="mes",
    )

    assert result["total_decisoes"] == 3
    assert len(result["serie_temporal"]) == 3
    assert result["tendencia"] in ["crescente", "decrescente", "estavel"]
    assert result["pico"]["count"] > 0
    assert result["media_por_periodo"] > 0


@pytest.mark.asyncio
async def test_analise_por_orgao_no_decisoes(db_session: AsyncSession):
    """Test organ analysis when no decisions match."""
    service = EstatisticasService(db_session)

    result = await service.analise_por_orgao("Órgão Inexistente")

    assert result["orgao"] == "Órgão Inexistente"
    assert result["total_decisoes"] == 0
    assert result["relatores"] == {}
    assert result["classes"] == {}
    assert result["top_relatores"] == []


@pytest.mark.asyncio
async def test_analise_por_orgao_with_decisoes(db_session: AsyncSession):
    """Test organ analysis with matching decisions."""
    service = EstatisticasService(db_session)

    # Create test decisions
    decisao1 = Decisao(
        uuid_tjdft="test-uuid-10",
        relator="João Silva",
        orgao_julgador="Turma Cível 1",
        classe="Apelação",
    )
    decisao2 = Decisao(
        uuid_tjdft="test-uuid-11",
        relator="Maria Santos",
        orgao_julgador="Turma Cível 1",
        classe="Agravo",
    )
    db_session.add_all([decisao1, decisao2])
    await db_session.flush()

    result = await service.analise_por_orgao("Turma Cível")

    assert result["total_decisoes"] == 2
    assert len(result["relatores"]) == 2
    assert len(result["classes"]) == 2
    assert len(result["top_relatores"]) == 2


@pytest.mark.asyncio
async def test_distribuicao_por_classe_no_decisoes(db_session: AsyncSession):
    """Test class distribution when no decisions exist."""
    service = EstatisticasService(db_session)

    result = await service.distribuicao_por_classe()

    assert result["total"] == 0
    assert result["classes"] == []
    assert result["top_5"] == []
    assert result["outras"] == 0


@pytest.mark.asyncio
async def test_distribuicao_por_classe_with_decisoes(db_session: AsyncSession):
    """Test class distribution with decisions."""
    service = EstatisticasService(db_session)

    # Create test decisions
    decisao1 = Decisao(
        uuid_tjdft="test-uuid-12",
        classe="Apelação",
    )
    decisao2 = Decisao(
        uuid_tjdft="test-uuid-13",
        classe="Apelação",
    )
    decisao3 = Decisao(
        uuid_tjdft="test-uuid-14",
        classe="Agravo",
    )
    db_session.add_all([decisao1, decisao2, decisao3])
    await db_session.flush()

    result = await service.distribuicao_por_classe()

    assert result["total"] == 3
    assert len(result["classes"]) == 2
    assert result["classes"][0]["classe"] == "Apelação"
    assert result["classes"][0]["count"] == 2
    assert result["classes"][0]["percentual"] > 0
    assert len(result["top_5"]) == 2


@pytest.mark.asyncio
async def test_ranking_relatores_no_decisoes(db_session: AsyncSession):
    """Test relator ranking when no decisions exist."""
    service = EstatisticasService(db_session)

    result = await service.ranking_relatores()

    assert result == []


@pytest.mark.asyncio
async def test_ranking_relatores_with_decisoes(db_session: AsyncSession):
    """Test relator ranking with decisions."""
    service = EstatisticasService(db_session)

    # Create test decisions
    decisao1 = Decisao(
        uuid_tjdft="test-uuid-15",
        relator="João Silva",
        orgao_julgador="Turma Cível",
    )
    decisao2 = Decisao(
        uuid_tjdft="test-uuid-16",
        relator="João Silva",
        orgao_julgador="Turma Cível",
    )
    decisao3 = Decisao(
        uuid_tjdft="test-uuid-17",
        relator="Maria Santos",
        orgao_julgador="Turma Cível",
    )
    db_session.add_all([decisao1, decisao2, decisao3])
    await db_session.flush()

    result = await service.ranking_relatores(limite=10)

    assert len(result) == 2
    assert result[0]["relator"] == "João Silva"
    assert result[0]["total"] == 2
    assert result[1]["relator"] == "Maria Santos"
    assert result[1]["total"] == 1


@pytest.mark.asyncio
async def test_comparar_periodos_no_decisoes(db_session: AsyncSession):
    """Test period comparison when no decisions exist."""
    service = EstatisticasService(db_session)

    result = await service.comparar_periodos(
        {"inicio": date(2024, 1, 1), "fim": date(2024, 1, 31)},
        {"inicio": date(2024, 2, 1), "fim": date(2024, 2, 28)},
    )

    assert result["periodo1"]["total"] == 0
    assert result["periodo2"]["total"] == 0
    assert result["tendencia"] == "estavel"


@pytest.mark.asyncio
async def test_comparar_periodos_with_decisoes(db_session: AsyncSession):
    """Test period comparison with decisions."""
    service = EstatisticasService(db_session)

    # Create test decisions - 5 in January, 3 in February
    for i in range(5):
        db_session.add(
            Decisao(
                uuid_tjdft=f"test-uuid-jan-{i}",
                data_julgamento=date(2024, 1, 15),
            )
        )
    for i in range(3):
        db_session.add(
            Decisao(
                uuid_tjdft=f"test-uuid-fev-{i}",
                data_julgamento=date(2024, 2, 15),
            )
        )
    await db_session.flush()

    result = await service.comparar_periodos(
        {"inicio": date(2024, 1, 1), "fim": date(2024, 1, 31)},
        {"inicio": date(2024, 2, 1), "fim": date(2024, 2, 28)},
    )

    assert result["periodo1"]["total"] == 5
    assert result["periodo2"]["total"] == 3
    assert result["variacao"] < 0  # Redução
    assert result["tendencia"] == "reducao"


def test_agrupar_por_periodo_dia():
    """Test grouping decisions by day."""
    service = EstatisticasService(MagicMock())

    decisao1 = Decisao(
        uuid_tjdft="test-uuid-18",
        data_julgamento=date(2024, 1, 15),
    )
    decisao2 = Decisao(
        uuid_tjdft="test-uuid-19",
        data_julgamento=date(2024, 1, 15),
    )

    result = service._agrupar_por_periodo([decisao1, decisao2], "dia")

    assert len(result) == 1
    assert result[0]["data"] == "2024-01-15"
    assert result[0]["count"] == 2


@pytest.mark.asyncio
async def test_calcular_tendencia_crescente(db_session: AsyncSession):
    """Test trend calculation for growing series."""
    service = EstatisticasService(db_session)

    serie = [
        {"data": "2024-01", "count": 10},
        {"data": "2024-02", "count": 20},
        {"data": "2024-03", "count": 30},
        {"data": "2024-04", "count": 40},
    ]

    tendencia = service._calcular_tendencia(serie)

    assert tendencia == "crescente"


@pytest.mark.asyncio
async def test_calcular_tendencia_decrescente(db_session: AsyncSession):
    """Test trend calculation for declining series."""
    service = EstatisticasService(db_session)

    serie = [
        {"data": "2024-01", "count": 40},
        {"data": "2024-02", "count": 30},
        {"data": "2024-03", "count": 20},
        {"data": "2024-04", "count": 10},
    ]

    tendencia = service._calcular_tendencia(serie)

    assert tendencia == "decrescente"


@pytest.mark.asyncio
async def test_extrair_temas(db_session: AsyncSession):
    """Test theme extraction from ementas."""
    service = EstatisticasService(db_session)

    ementas = [
        "Direito civil e processual civil. Apelação conhecida.",
        "Direito tributário. ICMS e taxa.",
        "Processo civil. Agravo de instrumento.",
    ]

    temas = service._extrair_temas(ementas)

    assert len(temas) > 0
    assert isinstance(temas, list)


def test_calcular_media_mensal():
    """Test monthly average calculation."""
    service = EstatisticasService(MagicMock())

    datas = [
        date(2024, 1, 15),
        date(2024, 2, 20),
        date(2024, 3, 10),
    ]

    media = service._calcular_media_mensal(datas)

    assert media == 1.0  # 3 decisions in 3 months
