"""
E2E tests for database integration with real PostgreSQL.

Tests verify that data is correctly persisted and retrieved from
the PostgreSQL container.
"""

import uuid

import pytest
from sqlalchemy import select

from app.models.consulta import Consulta


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_create_consulta_in_database(e2e_session):
    """Test creating a Consulta record directly in PostgreSQL."""
    # Arrange
    consulta_id = str(uuid.uuid4())
    consulta = Consulta(
        id=consulta_id,
        query="test query",
        filtros={"relator": "test-relator"},
        resultados_encontrados=10,
        pagina=1,
        tamanho=20,
        usuario_id="test-user",
    )

    # Act
    e2e_session.add(consulta)
    await e2e_session.commit()
    await e2e_session.refresh(consulta)

    # Assert
    assert consulta.id == consulta_id
    assert consulta.query == "test query"
    assert consulta.filtros == {"relator": "test-relator"}
    assert consulta.resultados_encontrados == 10
    assert consulta.criado_em is not None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_retrieve_consulta_from_database(e2e_session):
    """Test retrieving a Consulta record from PostgreSQL."""
    # Arrange
    consulta_id = str(uuid.uuid4())
    consulta = Consulta(
        id=consulta_id,
        query="retrieve test",
        filtros={"classe": "APC"},
        resultados_encontrados=5,
        pagina=1,
        tamanho=10,
    )
    e2e_session.add(consulta)
    await e2e_session.commit()

    # Act
    result = await e2e_session.execute(
        select(Consulta).where(Consulta.id == consulta_id)
    )
    retrieved = result.scalar_one()

    # Assert
    assert retrieved.id == consulta_id
    assert retrieved.query == "retrieve test"
    assert retrieved.filtros == {"classe": "APC"}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_update_consulta_in_database(e2e_session):
    """Test updating a Consulta record in PostgreSQL."""
    # Arrange
    consulta_id = str(uuid.uuid4())
    consulta = Consulta(
        id=consulta_id,
        query="original query",
        resultados_encontrados=1,
    )
    e2e_session.add(consulta)
    await e2e_session.commit()

    # Act
    consulta.resultados_encontrados = 100
    await e2e_session.commit()
    await e2e_session.refresh(consulta)

    # Assert
    assert consulta.resultados_encontrados == 100
    assert consulta.query == "original query"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_delete_consulta_from_database(e2e_session):
    """Test deleting a Consulta record from PostgreSQL."""
    # Arrange
    consulta_id = str(uuid.uuid4())
    consulta = Consulta(
        id=consulta_id,
        query="to be deleted",
        resultados_encontrados=0,
    )
    e2e_session.add(consulta)
    await e2e_session.commit()

    # Act
    await e2e_session.delete(consulta)
    await e2e_session.commit()

    # Assert
    result = await e2e_session.execute(
        select(Consulta).where(Consulta.id == consulta_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_jsonb_filter_query(e2e_session):
    """Test querying JSONB column with filters."""
    # Arrange - Create multiple consultas
    consulta1 = Consulta(
        id=str(uuid.uuid4()),
        query="test1",
        filtros={"relator": "desembargador-1", "classe": "APC"},
    )
    consulta2 = Consulta(
        id=str(uuid.uuid4()),
        query="test2",
        filtros={"relator": "desembargador-2", "classe": "AGI"},
    )
    e2e_session.add_all([consulta1, consulta2])
    await e2e_session.commit()

    # Act - Query by specific filter value
    result = await e2e_session.execute(
        select(Consulta).where(Consulta.filtros["relator"].astext == "desembargador-1")
    )
    results = result.scalars().all()

    # Assert
    assert len(results) == 1
    assert results[0].query == "test1"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multiple_consultas_pagination(e2e_session):
    """Test creating and querying multiple Consulta records."""
    # Arrange
    consultas = []
    for i in range(5):
        consulta = Consulta(
            id=str(uuid.uuid4()),
            query=f"query {i}",
            filtros={"page": i},
            resultados_encontrados=i * 10,
        )
        consultas.append(consulta)

    e2e_session.add_all(consultas)
    await e2e_session.commit()

    # Act - Query with limit
    result = await e2e_session.execute(
        select(Consulta).order_by(Consulta.resultados_encontrados).limit(3)
    )
    results = result.scalars().all()

    # Assert
    assert len(results) == 3
    assert results[0].resultados_encontrados == 0
    assert results[2].resultados_encontrados == 20


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_consulta_without_filters(e2e_session):
    """Test creating Consulta without filters (None value)."""
    # Arrange & Act
    consulta = Consulta(
        id=str(uuid.uuid4()),
        query="simple search",
        filtros=None,
        resultados_encontrados=5,
    )
    e2e_session.add(consulta)
    await e2e_session.commit()

    # Assert
    assert consulta.filtros is None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_transaction_rollback_on_error(e2e_session):
    """Test that transaction rolls back on error."""
    # Arrange
    consulta_id = str(uuid.uuid4())
    consulta = Consulta(
        id=consulta_id,
        query="before error",
        resultados_encontrados=1,
    )
    e2e_session.add(consulta)
    await e2e_session.commit()

    # Act - Simulate error and rollback
    consulta.query = "after error"
    await e2e_session.rollback()

    # Assert - Query should not be persisted
    result = await e2e_session.execute(
        select(Consulta).where(Consulta.id == consulta_id)
    )
    retrieved = result.scalar_one_or_none()

    # Original data should still be there
    if retrieved:
        assert retrieved.query == "before error"
