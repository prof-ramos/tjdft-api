# E2E Test Plan - TJDFT API

## Current State

- **148 unit tests** passing
- **88% coverage** across app/
- **Test infrastructure**: pytest + pytest-asyncio, in-memory SQLite
- **Existing markers**: `unit`, `integration`, `api`
- **Missing**: True end-to-end tests with real external dependencies

---

## What E2E Tests Should Cover

### 1. Full Request Flow (API → Service → TJDFT → Response)

```
Client → FastAPI Endpoint → Service → TJDFTClient → TJDFT API → Cache → DB → Response
```

### 2. External Dependencies

| Dependency | Current Test Approach | E2E Approach |
|------------|----------------------|--------------|
| TJDFT API | Mocked/Respx | Real API calls |
| Database | In-memory SQLite | Real PostgreSQL |
| Cache | In-memory fallback | Real Redis |
| OpenAI | Mocked | Optional real calls |

---

## Recommended Tools

### Core Framework
- **pytest** (already used) - run with `pytest -m e2e`
- **pytest-docker** or **testcontainers** - spin up real services
- **pytest-asyncio** (already used) - async test support

### Service Fixtures

```python
# tests/e2e/conftest.py

@pytest.fixture(scope="session")
def docker_postgres():
    """Real PostgreSQL container for E2E tests."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres.get_connection_url()

@pytest.fixture(scope="session")
def docker_redis():
    """Real Redis container for E2E tests."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis.get_connection_url()

@pytest.fixture
async def real_db_session(docker_postgres):
    """Session with real PostgreSQL."""
    engine = create_async_engine(docker_postgres)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine)() as session:
        yield session
```

---

## Test Scenarios

### E2E-01: Busca Simples com API Real

```python
@pytest.mark.e2e
async def test_busca_simples_api_real(api_client, real_cache, real_db):
    """Fluxo completo: API → TJDFT → Cache → DB"""

    payload = {"query": "tributário", "pagina": 0, "tamanho": 10}

    # 1. Request to API
    response = await api_client.post("/api/v1/busca/", json=payload)

    # 2. Validate response structure
    assert response.status_code == 200
    data = response.json()
    assert "resultados" in data
    assert "total" in data
    assert "consulta_id" in data

    # 3. Verify cache was populated
    cached = cache.get(f"busca:{payload['query']}")
    assert cached is not None

    # 4. Verify DB has consulta record
    stmt = select(Consulta).where(Consulta.query == "tributário")
    result = await real_db.execute(stmt)
    assert result.scalar_one_or_none() is not None
```

### E2E-02: Busca com Filtros Avançados

```python
@pytest.mark.e2e
async def test_busca_com_relator_filtro(api_client):
    """Testa filtro por relator com nome exato."""

    payload = {
        "query": "",
        "relator": "TEÓFILO CAETANO",
        "pagina": 0,
        "tamanho": 20
    }

    response = await api_client.post("/api/v1/busca/", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Todos os resultados devem ser do relator filtrado
    for r in data["resultados"]:
        assert r["relator"] == "TEÓFILO CAETANO"
```

### E2E-03: Paginação Completa

```python
@pytest.mark.e2e
async def test_paginação_multiplas_paginas(api_client):
    """Testa paginação através de múltiplas chamadas."""

    payload = {"query": "direito civil", "tamanho": 20}

    # Primeira página
    response1 = await api_client.post("/api/v1/busca/", json={**payload, "pagina": 0})
    data1 = response1.json()
    ids_pagina1 = {r["id"] for r in data1["resultados"]}

    # Segunda página
    response2 = await api_client.post("/api/v1/busca/", json={**payload, "pagina": 1})
    data2 = response2.json()
    ids_pagina2 = {r["id"] for r in data2["resultados"]}

    # Sem sobreposição de IDs
    assert ids_pagina1.isdisjoint(ids_pagina2)
```

### E2E-04: Cache Hit (Segunda Requisição)

```python
@pytest.mark.e2e
async def test_cache_hit_evita_chamada_api(api_client, real_cache):
    """Segunda chamada igual deve usar cache."""

    payload = {"query": "consumidor", "pagina": 0, "tamanho": 10}

    # Primeira chamada - deve ir à API
    with RespxMock(assert_all_called=False) as respx:
        respx.post("https://jurisdf.tjdft.jus.br/api/v1/pesquisa").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        response1 = await api_client.post("/api/v1/busca/", json=payload)

    # Segunda chamada - deve usar cache (API não é chamada)
    with RespxMock(assert_all_called=False) as respx:
        respx.post("https://jurisdf.tjdft.jus.br/api/v1/pesquisa").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        response2 = await api_client.post("/api/v1/busca/", json=payload)

    # A mesma rota não foi chamada (cache hit)
    assert not respx["https://jurisdf.tjdft.jus.br/api/v1/pesquisa"].called
```

### E2E-05: Filtro de Turmas Recursais

```python
@pytest.mark.e2e
async def test_excluir_turmas_recursais(api_client):
    """Testa remoção de juizados especiais."""

    payload = {
        "query": "indenizatório",
        "excluir_turmas_recursais": True
    }

    response = await api_client.post(
        "/api/v1/busca/?excluir_turmas_recursais=true",
        json=payload
    )

    data = response.json()

    # Nenhum resultado deve ser de juizado especial
    for r in data["resultados"]:
        assert r.get("instancia") != "juizado_especial"
        assert "turma recursal" not in r.get("orgao_julgador", "").lower()
```

### E2E-06: Tratamento de Erro da API TJDFT

```python
@pytest.mark.e2e
async def test_api_tjdft_timeout(api_client):
    """Timeout na API TJDFT deve retornar erro tratado."""

    with RespxMock() as respx:
        # Simula timeout
        route = respx.post("https://jurisdf.tjdft.jus.br/api/v1/pesquisa").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        response = await api_client.post(
            "/api/v1/busca/",
            json={"query": "teste", "pagina": 0, "tamanho": 10}
        )

        # Deve retornar erro 503 ou similar
        assert response.status_code in [503, 504]
```

### E2E-07: Enriquecimento de Dados

```python
@pytest.mark.e2e
async def test_enriquecimento_densidade_instancia(api_client):
    """Verifica campos de enriquecimento nos resultados."""

    response = await api_client.post(
        "/api/v1/busca/",
        json={"query": "aposentadoria", "pagina": 0, "tamanho": 5}
    )

    data = response.json()

    for r in data["resultados"]:
        # Campos de enriquecimento devem estar presentes
        assert "densidade_precedentes" in r
        assert r["densidade_precedentes"] in ["escasso", "moderado", "consolidado", "massivo"]

        assert "instancia" in r
        assert r["instancia"] in ["juizado_especial", "tjdft_2a_instancia", None]
```

### E2E-08: Histórico de Consultas

```python
@pytest.mark.e2e
async def test_historico_consultas_usuario(api_client):
    """Testa recuperação de histórico por usuário."""

    user_id = str(uuid.uuid4())

    # Fazer 3 buscas
    for query in ["tributário", "trabalhista", "consumidor"]:
        await api_client.post(
            "/api/v1/busca/",
            json={"query": query, "pagina": 0, "tamanho": 5},
            headers={"X-User-ID": user_id}
        )

    # Recuperar histórico
    response = await api_client.get(f"/api/v1/historico/?usuario_id={user_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["consultas"]) == 3
```

---

## File Structure

```
tests/
├── e2e/
│   ├── __init__.py
│   ├── conftest.py          # E2E fixtures (docker, real services)
│   ├── test_busca_e2e.py    # Busca endpoints E2E
│   ├── test_cache_e2e.py    # Redis integration
│   └── test_database_e2e.py # PostgreSQL integration
├── unit/                    # Existing unit tests
├── integration/             # Existing integration tests
└── conftest.py              # Shared fixtures
```

---

## Running E2E Tests

### All E2E Tests
```bash
pytest -m e2e
```

### With Coverage
```bash
pytest -m e2e --cov=app --cov-report=html
```

### Specific Test File
```bash
pytest tests/e2e/test_busca_e2e.py -v
```

### CI/CD Integration
```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]
jobs:
  e2e:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v4
      - run: pytest -m e2e
```

---

## Dependencies to Add

```toml
# pyproject.toml
[project.optional-dependencies]
e2e = [
    "testcontainers>=4.0.0",  # Docker fixtures
    "pytest-docker>=3.0.0",   # Alternative to testcontainers
]
```

---

## Implementation Checklist

- [ ] Create `tests/e2e/` directory structure
- [ ] Add E2E marker to `pyproject.toml`
- [ ] Create `tests/e2e/conftest.py` with docker fixtures
- [ ] Implement `test_busca_e2e.py` (scenarios 1-5)
- [ ] Implement `test_cache_e2e.py` (scenario 4)
- [ ] Implement `test_error_e2e.py` (scenario 6)
- [ ] Add `e2e` optional dependency group
- [ ] Update CI workflow to run E2E tests
- [ ] Document E2E test running in README

---

## Notes

1. **Rate Limiting**: TJDFT API may have rate limits - add delays or use test account
2. **Data Volatility**: Real API data changes - use flexible assertions
3. **Slow Tests**: E2E tests are slower - run separately from unit tests
4. **Flaky Tests**: Network issues can cause flakiness - add retries
5. **Test Data**: Consider a test-specific TJDFT endpoint if available
