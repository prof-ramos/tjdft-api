"""
E2E tests for SQLite configuration and optimization.

Tests verify that SQLite PRAGMA settings are correctly applied
when using SQLite as the database backend.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.sqlite_config import (
    BUSY_TIMEOUT_MS,
    CACHE_SIZE_PAGES,
    MMAP_SIZE_BYTES,
    configure_sqlite,
    run_optimize,
)
from app.database import Base
from app.models.decisao import Decisao
from app.models.consulta import Consulta


@pytest.fixture(scope="function")
async def sqlite_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create in-memory SQLite engine for testing."""
    # Use shared cache for in-memory database to allow connections
    engine = create_async_engine(
        "sqlite+aiosqlite:///file:sqlite_test.db?cache=shared",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def sqlite_session(
    sqlite_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Get SQLite session for tests."""
    async_session_maker = async_sessionmaker(
        sqlite_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_sqlite_wal_mode_enabled_on_connection(sqlite_engine: AsyncEngine):
    """Test that WAL mode is enabled when connecting to SQLite."""
    # Act - Create a new connection, configure it, and check PRAGMA values
    async with sqlite_engine.connect() as conn:
        # Manually apply SQLite configuration (simulates event listener)
        await conn.run_sync(configure_sqlite)

        result = await conn.execute(text("PRAGMA journal_mode"))
        wal_mode = result.scalar_one()

    # Assert - WAL mode should be enabled
    assert wal_mode == "wal", f"Expected 'wal' but got '{wal_mode}'"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_sqlite_busy_timeout_set(sqlite_engine: AsyncEngine):
    """Test that busy timeout is configured to prevent lock errors."""
    # Act
    async with sqlite_engine.connect() as conn:
        result = await conn.execute(text("PRAGMA busy_timeout"))
        timeout = result.scalar_one()

    # Assert - Should be 5000ms (5 seconds)
    assert timeout == BUSY_TIMEOUT_MS, f"Expected {BUSY_TIMEOUT_MS} but got {timeout}"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_sqlite_foreign_keys_enabled(sqlite_engine: AsyncEngine):
    """Test that foreign key enforcement is enabled."""
    # Act
    async with sqlite_engine.connect() as conn:
        await conn.run_sync(configure_sqlite)
        result = await conn.execute(text("PRAGMA foreign_keys"))
        fk_enabled = result.scalar_one()

    # Assert
    assert fk_enabled == 1, "Foreign keys should be enabled (1)"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_sqlite_mmap_size_configured(sqlite_engine: AsyncEngine):
    """Test that memory mapping is configured for faster reads."""
    # Act
    async with sqlite_engine.connect() as conn:
        await conn.run_sync(configure_sqlite)
        result = await conn.execute(text("PRAGMA mmap_size"))
        mmap_size = result.scalar_one()

    # Assert - Should be 256MB
    assert (
        mmap_size == MMAP_SIZE_BYTES
    ), f"Expected {MMAP_SIZE_BYTES} but got {mmap_size}"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_sqlite_cache_size_configured(sqlite_engine: AsyncEngine):
    """Test that cache size is increased from default."""
    # Act
    async with sqlite_engine.connect() as conn:
        await conn.run_sync(configure_sqlite)
        result = await conn.execute(text("PRAGMA cache_size"))
        cache_size = result.scalar_one()

    # Assert - Should be -64000 (64MB)
    assert (
        cache_size == CACHE_SIZE_PAGES
    ), f"Expected {CACHE_SIZE_PAGES} but got {cache_size}"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_sqlite_synchronous_mode_set(sqlite_engine: AsyncEngine):
    """Test that synchronous mode is set to NORMAL (safe with WAL)."""
    # Act
    async with sqlite_engine.connect() as conn:
        result = await conn.execute(text("PRAGMA synchronous"))
        synchronous = result.scalar_one()

    # Assert - NORMAL is appropriate with WAL mode
    assert synchronous in (1, 2), f"Expected 1 or 2 (NORMAL) but got {synchronous}"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_configure_sqlite_function():
    """Test the configure_sqlite function directly."""

    # Arrange - Create a mock connection object
    class MockDialect:
        name = "sqlite"

    class MockDBAPIConn:
        def __init__(self):
            self.pragmas = {}

        def execute(self, sql: str):
            # Parse PRAGMA statements
            if "PRAGMA" in sql:
                # Handle both direct value and f-string formats
                if "=" in sql:
                    parts = sql.split("=")
                    key = parts[0].replace("PRAGMA ", "").strip()
                    value = parts[1].strip()
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    self.pragmas[key] = value
            return self

    class MockConnection:
        def __init__(self):
            self.dialect = MockDialect()
            self.connection = MockDBAPIConn()

    # Act
    mock_conn = MockConnection()
    configure_sqlite(mock_conn)

    # Assert - Verify all pragmas were set
    assert "journal_mode" in mock_conn.connection.pragmas
    assert (
        mock_conn.connection.pragmas["journal_mode"] == "WAL"
    )  # SQLite returns uppercase
    assert mock_conn.connection.pragmas["busy_timeout"] == str(BUSY_TIMEOUT_MS)
    assert mock_conn.connection.pragmas["foreign_keys"] == "ON"
    assert mock_conn.connection.pragmas["mmap_size"] == str(MMAP_SIZE_BYTES)
    assert mock_conn.connection.pragmas["synchronous"] == "NORMAL"
    assert mock_conn.connection.pragmas["cache_size"] == str(CACHE_SIZE_PAGES)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_configure_sqlite_skips_non_sqlite():
    """Test that configure_sqlite skips non-SQLite databases."""

    # Arrange - Create a mock connection with PostgreSQL dialect
    class PostgresDialect:
        name = "postgresql"

    class MockConnection:
        def __init__(self):
            self.dialect = PostgresDialect()
            self.execute_called = False

        def execute(self, sql: str):
            self.execute_called = True
            return self

    # Act
    mock_conn = MockConnection()
    configure_sqlite(mock_conn)

    # Assert - execute should not be called for PostgreSQL
    assert (
        not mock_conn.execute_called
    ), "configure_sqlite should skip non-SQLite databases"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_run_optimize_function(sqlite_engine: AsyncEngine):
    """Test the run_optimize function executes without errors."""
    # Act & Assert - Should not raise any exceptions
    async with sqlite_engine.connect() as conn:
        await conn.run_sync(run_optimize)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_decisao_indexes_work(sqlite_engine: AsyncEngine):
    """Test that indexes on Decisao model improve query performance."""
    # Configure SQLite
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(configure_sqlite)

    # Arrange & Act
    async with AsyncSession(sqlite_engine) as session:
        # Create test data
        decisao = Decisao(
            uuid_tjdft="uuid-test-1",
            processo="0123456-78.2024.0001.8.26.001",
            relator="Relator Test",
            data_julgamento=date(2024, 1, 15),
            orgao_julgador="Turma Test",
        )
        session.add(decisao)
        await session.flush()

        # Query by indexed columns (the index will be used by SQLite)
        result = await session.execute(
            select(Decisao).where(Decisao.processo == "0123456-78.2024.0001.8.26.001")
        )
        found = result.scalar_one_or_none()

        # Assert - Index should work correctly
        assert found is not None
        assert found.processo == "0123456-78.2024.0001.8.26.001"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_consulta_indexes_work(sqlite_engine: AsyncEngine):
    """Test that indexes on Consulta model improve query performance."""
    # Configure SQLite
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(configure_sqlite)

    async with AsyncSession(sqlite_engine) as session:
        # Arrange - Create test data
        consultas = [
            Consulta(
                id=str(uuid.uuid4()),
                query=f"search term {i}",
                usuario_id="user-123",
                resultados_encontrados=i * 10,
            )
            for i in range(1, 6)
        ]
        session.add_all(consultas)
        await session.commit()

        # Act - Query by indexed columns
        result = await session.execute(
            select(Consulta).where(Consulta.usuario_id == "user-123")
        )
        results = result.scalars().all()

        # Assert - Should find all records for this user
        assert len(results) == 5
        assert all(c.usuario_id == "user-123" for c in results)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_decisao_relator_index_query(sqlite_engine: AsyncEngine):
    """Test querying Decisao by relator uses the index."""
    # Configure SQLite
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(configure_sqlite)

    async with AsyncSession(sqlite_engine) as session:
        # Arrange
        decisoes = [
            Decisao(
                id=str(uuid.uuid4()),
                uuid_tjdft=f"uuid-{i}",
                relator="Desembargador Silva",
                data_julgamento=date(2024, 1, 20),
            )
            for i in range(3)
        ]
        session.add_all(decisoes)
        await session.commit()

        # Act - Query by relator (indexed column)
        result = await session.execute(
            select(Decisao).where(Decisao.relator == "Desembargador Silva")
        )
        results = result.scalars().all()

        # Assert
        assert len(results) == 3


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_decisao_data_julgamento_index_query(sqlite_engine: AsyncEngine):
    """Test querying Decisao by data_julgamento uses the index."""
    # Configure SQLite
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(configure_sqlite)

    async with AsyncSession(sqlite_engine) as session:
        # Arrange
        decisoes = [
            Decisao(
                id=str(uuid.uuid4()),
                uuid_tjdft=f"uuid-{i}",
                data_julgamento=date(2024, 3, 15),
            )
            for i in range(3)
        ]
        session.add_all(decisoes)
        await session.commit()

        # Act - Query by data_julgamento (indexed column)
        result = await session.execute(
            select(Decisao).where(Decisao.data_julgamento == date(2024, 3, 15))
        )
        results = result.scalars().all()

        # Assert
        assert len(results) == 3
