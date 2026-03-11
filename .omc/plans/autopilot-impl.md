# E2E Test Infrastructure - Implementation Plan

## Overview
This plan details the implementation of end-to-end testing for TJDFT API using real external dependencies (PostgreSQL, Redis, TJDFT API) via Docker/testcontainers.

## Current State Analysis
- **Existing tests**: 148 unit tests using in-memory SQLite and mocked HTTP
- **Test infrastructure**: `/Users/gabrielramos/tjdft-api/tests/conftest.py` has SQLite fixtures
- **Service layer**: `/Users/gabrielramos/tjdft-api/app/services/busca_service.py` (lines 45-669) - uses `TJDFTClient`, `CacheManager`
- **Cache**: `/Users/gabrielramos/tjdft-api/app/utils/cache.py` - Redis with in-memory fallback
- **Database**: `/Users/gabrielramos/tjdft-api/app/database.py` - SQLAlchemy async with PostgreSQL support
- **CI/CD**: No GitHub Actions workflows exist yet

---

## Phase 1: Dependencies and Setup

### 1.1 Python Packages to Add

Add to `requirements-dev.txt`:

```txt
# E2E Testing with testcontainers
testcontainers>=4.7.0
pytest-docker>=3.0.0  # Alternative to testcontainers

# Additional E2E utilities
pytest-timeout>=2.3.0  # Timeout for real API calls
```

**Decision**: Use `testcontainers` as primary choice (better Python pytest integration), `pytest-docker` as fallback.

### 1.2 File Creation Order

```
tests/e2e/
├── __init__.py                    # 1st: Empty marker file
├── conftest.py                    # 2nd: Docker fixtures (PostgreSQL, Redis)
├── fixtures/                      # 3rd: Shared fixtures
│   ├── __init__.py
│   ├── tjdft_api.py              # TJDFT API fixtures
│   └── data.py                   # Test data factories
├── test_busca_e2e.py             # 4th: Main E2E scenarios
├── test_cache_e2e.py             # 5th: Cache-specific tests
└── test_database_e2e.py          # 6th: Database integration tests
```

---

## Phase 2: Docker Fixture Setup (`tests/e2e/conftest.py`)

### 2.1 PostgreSQL Container Fixture

```python
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for E2E tests."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def e2e_database_url(postgres_container) -> str:
    """Get async connection URL for PostgreSQL container."""
    connection_url = postgres_container.get_connection_url()
    # Convert to async URL
    return connection_url.replace("postgresql://", "postgresql+asyncpg://")

@pytest.fixture(scope="function")
async def e2e_engine(e2e_database_url):
    """Create async engine for E2E tests."""
    engine = create_async_engine(e2e_database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
```

### 2.2 Redis Container Fixture

```python
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container for E2E tests."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis

@pytest.fixture(scope="function")
def e2e_cache_manager(redis_container) -> CacheManager:
    """Create CacheManager pointing to container Redis."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return CacheManager(redis_host=host, redis_port=int(port))
```

### 2.3 Test Marker Configuration

Create `pytest.ini` (or update existing):

```ini
[pytest]
markers =
    e2e: End-to-end tests (requires Docker)
    slow: Slow-running tests
    integration: Integration tests
    unit: Unit tests
testpaths = tests
asyncio_mode = auto
```

---

## Phase 3: TJDFT API Integration (`tests/e2e/fixtures/tjdft_api.py`)

### 3.1 Real API vs Mock Toggle

```python
import os
from typing import AsyncGenerator
from httpx import AsyncClient

USE_REAL_TJDFT_API = os.getenv("E2E_USE_REAL_TJDFT", "false").lower() == "true"

@pytest.fixture(scope="session")
def tjdft_api_base_url() -> str:
    """Get TJDFT API base URL."""
    if USE_REAL_TJDFT_API:
        return "https://jurisdf.tjdft.jus.br/api/v1/pesquisa"
    # Mock server URL for CI/CD (use pytest-httpx or similar)
    return "http://localhost:9999/api/v1/pesquisa"

@pytest.fixture
async def real_tjdft_client(e2e_cache_manager: CacheManager):
    """Create real TJDFT client for E2E tests."""
    async with TJDFTClient(cache_manager=e2e_cache_manager) as client:
        yield client
```

### 3.2 Rate Limiting Handler

```python
import asyncio
from typing import Callable

async def with_rate_limit(func: Callable, delay: float = 0.5):
    """Execute function with rate limiting delay."""
    result = await func()
    await asyncio.sleep(delay)
    return result

@pytest.fixture
def rate_limited_request():
    """Wrapper for rate-limited requests."""
    return with_rate_limit
```

---

## Phase 4: Test Scenario Implementation Sequence

### Scenario 1: Full Request Flow (API -> Service -> TJDFT -> Response)

**File**: `tests/e2e/test_busca_e2e.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_request_flow(
    api_client: AsyncClient,
    e2e_engine: AsyncEngine,
    e2e_cache_manager: CacheManager,
):
    """Test complete flow: HTTP request -> service -> TJDFT API -> response."""
    # Arrange
    request_payload = {"query": "tributário", "pagina": 1, "tamanho": 5}

    # Act
    response = await api_client.post("/api/v1/busca/", json=request_payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "resultados" in data
    assert "total" in data
    assert "consulta_id" in data
```

### Scenario 2: Cache Integration with Real Redis

**File**: `tests/e2e/test_cache_e2e.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_hit_returns_same_data(
    e2e_cache_manager: CacheManager,
    real_tjdft_client: TJDFTClient,
):
    """Test that cache returns same data on second call."""
    # First call - cache miss
    result1 = await real_tjdft_client.buscar_simples("tributário", pagina=0)

    # Second call - cache hit
    result2 = await real_tjdft_client.buscar_simples("tributário", pagina=0)

    assert result1["total"] == result2["total"]
    assert len(result1["registros"]) == len(result2["registros"])
```

### Scenario 3: Database Integration with PostgreSQL

**File**: `tests/e2e/test_database_e2e.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_consulta_saved_to_postgresql(
    api_client: AsyncClient,
    e2e_session: AsyncSession,
):
    """Test that consulta is persisted to PostgreSQL."""
    # Act
    response = await api_client.post("/api/v1/busca/", json={"query": "teste"})
    consulta_id = response.json()["consulta_id"]

    # Assert - query directly from PostgreSQL
    from sqlalchemy import select
    from app.models.consulta import Consulta
    result = await e2e_session.execute(
        select(Consulta).where(Consulta.id == uuid.UUID(consulta_id))
    )
    consulta = result.scalar_one()
    assert consulta.query == "teste"
```

### Scenario 4: Error Handling (Timeouts)

**File**: `tests/e2e/test_busca_e2e.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_timeout_handling(
    api_client: AsyncClient,
    monkeypatch,
):
    """Test timeout is handled gracefully."""
    from app.services import tjdft_client

    # Patch timeout to very low value
    monkeypatch.setattr(tjdft_client.TJDFTClient, "DEFAULT_TIMEOUT", 0.001)

    response = await api_client.post("/api/v1/busca/", json={"query": "test"})

    # Should handle timeout gracefully
    assert response.status_code in [500, 503, 504]  # Or appropriate error response
```

### Scenario 5: Data Enrichment Verification

**File**: `tests/e2e/test_busca_e2e.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_data_enrichment_adds_instancia(
    api_client: AsyncClient,
):
    """Test that response includes instancia field."""
    response = await api_client.post("/api/v1/busca/", json={"query": "teste"})

    assert response.status_code == 200
    data = response.json()
    if data["resultados"]:
        resultado = data["resultados"][0]
        assert "instancia" in resultado
        assert "resumo_relevancia" in resultado
```

### Scenario 6: Pagination Across Multiple Pages

**File**: `tests/e2e/test_busca_e2e.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_pagination_returns_different_results(
    api_client: AsyncClient,
):
    """Test that pagination returns different pages."""
    response1 = await api_client.post(
        "/api/v1/busca/", json={"query": "", "pagina": 1, "tamanho": 5}
    )
    response2 = await api_client.post(
        "/api/v1/busca/", json={"query": "", "pagina": 2, "tamanho": 5}
    )

    data1 = response1.json()["resultados"]
    data2 = response2.json()["resultados"]

    # Should have different results (or empty second page)
    assert len(data1) > 0
```

### Scenario 7: Filter Validation (Relator, Classe, Orgao)

**File**: `tests/e2e/test_busca_e2e.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_filter_by_relator(
    api_client: AsyncClient,
):
    """Test filtering by relator."""
    response = await api_client.post(
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
    # All results should have the specified relator
    for result in data["resultados"]:
        assert "faustolo" in result.get("relator", "").lower()
```

### Scenario 8: Turmas Recursais Exclusion

**File**: `tests/e2e/test_busca_e2e.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_excluir_turmas_recursais(
    api_client: AsyncClient,
):
    """Test turmas recursais are excluded when requested."""
    response = await api_client.post(
        "/api/v1/busca/",
        json={"query": "", "pagina": 1, "tamanho": 20},
        params={"excluir_turmas_recursais": True},
    )

    assert response.status_code == 200
    data = response.json()
    for result in data["resultados"]:
        assert result.get("instancia") != "juizado_especial"
```

---

## Phase 5: E2E Conftest Complete Setup

**File**: `tests/e2e/conftest.py` (complete)

```python
"""
E2E test configuration with Docker containers for PostgreSQL and Redis.
"""
import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.main import app
from app.utils.cache import CacheManager

# Import testcontainers (may not be available in all environments)
try:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False
    pytest.skip("testcontainers not installed", allow_module_level=True)


# Environment flag for using real TJDFT API
USE_REAL_TJDFT = os.getenv("E2E_USE_REAL_TJDFT", "false").lower() == "true"


@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    """Start PostgreSQL container for E2E tests."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container() -> RedisContainer:
    """Start Redis container for E2E tests."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
def e2e_database_url(postgres_container: PostgresContainer) -> str:
    """Get async connection URL for PostgreSQL container."""
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
def e2e_cache_manager(redis_container: RedisContainer) -> CacheManager:
    """Create CacheManager pointing to container Redis."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return CacheManager(redis_host=host, redis_port=int(port))


@pytest_asyncio.fixture
async def e2e_api_client(
    e2e_session: AsyncSession,
    e2e_cache_manager: CacheManager,
) -> AsyncGenerator[AsyncClient, None]:
    """Create FastAPI test client with real dependencies."""
    from app.database import get_session
    from httpx import ASGITransport, AsyncClient

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
```

---

## Phase 6: CI/CD Integration

### 6.1 GitHub Actions Workflow

**File**: `.github/workflows/e2e-tests.yml`

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: tjdft_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run E2E tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/tjdft_test
          REDIS_URL: redis://localhost:6379
          E2E_USE_REAL_TJDFT: false  # Use mocks in CI
        run: |
          pytest -m e2e -v --tb=short --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: e2e
```

### 6.2 Local E2E Testing Script

**File**: `scripts/run-e2e.sh`

```bash
#!/bin/bash
# Run E2E tests locally

export E2E_USE_REAL_TJDFT="${E2E_USE_REAL_TJDFT:-true}"
export DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/tjdft_test"
export REDIS_URL="redis://localhost:6379"

echo "Running E2E tests with real TJDFT API: $E2E_USE_REAL_TJDFT"
pytest -m e2e -v --tb=short "$@"
```

---

## Phase 7: Mock Server for CI/CD

When real API calls are not desirable in CI, create a mock server:

**File**: `tests/e2e/mocks/tjdft_mock_server.py`

```python
"""Mock TJDFT API server for CI/CD testing."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/api/v1/pesquisa")
async def mock_search(request: dict):
    """Mock search endpoint."""
    return JSONResponse({
        "registros": [
            {
                "uuid": "mock-uuid-1",
                "numeroProcesso": "0700001-00.2024.8.07.0001",
                "ementa": "Mock ementa for testing",
                "nomeRelator": "Mock Relator",
                "dataJulgamento": "2024-01-15",
                "descricaoOrgaoJulgador": "1ª Turma Cível",
                "descricaoClasseCnj": "APELAÇÃO CÍVEL",
                "turmaRecursal": False,
                "subbase": "acordaos",
            }
        ],
        "total": 1,
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9999)
```

---

## Phase 8: Documentation Updates

### 8.1 Update CLAUDE.md

Add E2E testing section:

```markdown
## E2E Testing

### Running E2E Tests

```bash
# With real TJDFT API (local dev)
E2E_USE_REAL_TJDFT=true pytest -m e2e

# With mock server (CI/CD)
pytest -m e2e

# Specific scenario
pytest tests/e2e/test_busca_e2e.py::test_full_request_flow -v
```

### E2E Test Prerequisites

- Docker and Docker Compose installed
- For real API tests: internet connection to TJDFT API
```

### 8.2 Update README.md

Add E2E testing badge and section.

---

## Implementation Checklist

### Phase 1: Foundation (Day 1)
- [ ] Add testcontainers to requirements-dev.txt
- [ ] Create `tests/e2e/` directory structure
- [ ] Create `tests/e2e/__init__.py`
- [ ] Create `tests/e2e/conftest.py` with Docker fixtures
- [ ] Configure pytest markers in pytest.ini

### Phase 2: Infrastructure (Day 1-2)
- [ ] Implement PostgreSQL container fixture
- [ ] Implement Redis container fixture
- [ ] Implement e2e_api_client fixture
- [ ] Verify containers start/stop correctly

### Phase 3: Scenarios (Day 2-3)
- [ ] Scenario 1: Full request flow
- [ ] Scenario 2: Cache integration
- [ ] Scenario 3: Database integration
- [ ] Scenario 4: Error handling (timeouts)
- [ ] Scenario 5: Data enrichment verification
- [ ] Scenario 6: Pagination
- [ ] Scenario 7: Filter validation
- [ ] Scenario 8: Turmas recursais exclusion

### Phase 4: CI/CD (Day 3-4)
- [ ] Create GitHub Actions workflow
- [ ] Create mock server for CI
- [ ] Add run-e2e.sh script
- [ ] Test CI workflow locally with act

### Phase 5: Polish (Day 4-5)
- [ ] Update documentation
- [ ] Add rate limiting for real API calls
- [ ] Add test isolation cleanup
- [ ] Verify all E2E tests pass
- [ ] Measure and optimize test execution time

---

## Trade-offs Analysis

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| testcontainers | Clean lifecycle, cross-platform, pytest-native | Longer startup time, requires Docker | **Primary** |
| pytest-docker | Simpler setup, faster | Less flexible, Python-specific | Fallback |
| Real TJDFT API in CI | Complete confidence | Flaky, slow, external dependency | **Optional** |
| Mock TJDFT API | Fast, reliable, deterministic | May miss real API changes | **Primary for CI** |
| Separate E2E dir | Clear separation, marker-based | Duplicate fixtures | **Use** |
| Shared conftest | DRY, single fixture source | Mixed unit/integration concerns | **Already exists, keep E2E separate** |

---

## References

- `/Users/gabrielramos/tjdft-api/tests/conftest.py` - Existing unit test fixtures (SQLite)
- `/Users/gabrielramos/tjdft-api/app/services/busca_service.py` - Service layer to test
- `/Users/gabrielramos/tjdft-api/app/utils/cache.py` - Cache manager (lines 24-323)
- `/Users/gabrielramos/tjdft-api/app/database.py` - Database setup (lines 10-22)
- `/Users/gabrielramos/tjdft-api/app/api/v1/endpoints/busca.py` - Endpoint to test
