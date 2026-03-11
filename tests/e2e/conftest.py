"""
E2E test configuration with Docker containers for PostgreSQL and Redis.

This module provides pytest fixtures for running end-to-end tests with real
dependencies via testcontainers. Tests are marked with @pytest.mark.e2e.

Environment Variables:
    E2E_USE_REAL_TJDFT: Use real TJDFT API (true) or mock (false). Default: false.
    DATABASE_URL: Override PostgreSQL connection URL.
    REDIS_URL: Override Redis connection URL.
"""

import logging
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base, get_session
from app.main import app
from app.utils.cache import CacheManager

logger = logging.getLogger(__name__)

# Environment configuration
USE_REAL_TJDFT = os.getenv("E2E_USE_REAL_TJDFT", "false").lower() == "true"
USE_DOCKER = os.getenv("E2E_USE_DOCKER", "true").lower() == "true"

# Allow override via environment variables for local development
DB_URL = os.getenv("E2E_DATABASE_URL", "")
REDIS_URL = os.getenv("E2E_REDIS_URL", "")


# Import testcontainers (may not be available in all environments)
TESTCONTAINERS_AVAILABLE = False
try:
    from testcontainers.core.docker_client import DockerClient

    # Check if Docker daemon is running
    try:
        DockerClient().get_version()
        TESTCONTAINERS_AVAILABLE = True
    except Exception as e:
        logger.warning("Docker daemon not available: %s", e)
        TESTCONTAINERS_AVAILABLE = False
except ImportError as e:
    logger.warning("testcontainers not installed: %s", e)
    TESTCONTAINERS_AVAILABLE = False


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for E2E tests."""
    if not USE_DOCKER or not TESTCONTAINERS_AVAILABLE:
        pytest.skip(
            "Docker not available or disabled - "
            "set E2E_DATABASE_URL or E2E_USE_DOCKER=false"
        )
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container for E2E tests."""
    if not USE_DOCKER or not TESTCONTAINERS_AVAILABLE:
        pytest.skip(
            "Docker not available or disabled - "
            "set E2E_REDIS_URL or E2E_USE_DOCKER=false"
        )
    from testcontainers.redis import RedisContainer

    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
def e2e_database_url(postgres_container) -> str:
    """Get async connection URL for PostgreSQL container."""
    if DB_URL:
        return DB_URL
    url = postgres_container.get_connection_url()
    return url.replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture(scope="function")
async def e2e_engine(e2e_database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine with PostgreSQL container."""
    engine = create_async_engine(e2e_database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def e2e_session_maker(
    e2e_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create session maker for E2E tests."""
    return async_sessionmaker(
        e2e_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def e2e_session(
    e2e_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for E2E tests."""
    async with e2e_session_maker() as session:
        yield session


@pytest.fixture
def e2e_cache_manager(redis_container) -> CacheManager:
    """Create CacheManager pointing to container Redis."""
    if REDIS_URL:
        return CacheManager(redis_url=REDIS_URL)
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return CacheManager(redis_host=host, redis_port=int(port))


@pytest_asyncio.fixture
async def e2e_api_client(
    e2e_session: AsyncSession,
    e2e_cache_manager: CacheManager,
) -> AsyncGenerator[AsyncClient, None]:
    """Create FastAPI test client with real dependencies."""

    async def _get_e2e_session() -> AsyncGenerator[AsyncSession, None]:
        yield e2e_session

    app.dependency_overrides[get_session] = _get_e2e_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# Session-level fixtures for expensive operations
@pytest.fixture(scope="session")
def tjdft_api_base_url() -> str:
    """Get TJDFT API base URL (real or mock)."""
    if USE_REAL_TJDFT:
        return "https://jurisdf.tjdft.jus.br/api/v1/pesquisa"
    return "http://localhost:9999/api/v1/pesquisa"  # Mock server for CI
