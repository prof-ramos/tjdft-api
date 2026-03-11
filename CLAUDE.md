# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão Geral do Projeto

**TJDFT API** é uma API FastAPI para consulta de jurisprudência do Tribunal de Justiça do Distrito Federal e Territórios.

### Stack
- Python 3.11+, FastAPI 0.109+, SQLAlchemy 2.0+, Pydantic v2, httpx, pytest
- SQLite (dev) / PostgreSQL (prod)
- Redis para cache com fallback in-memory

## Comandos

### Desenvolvimento Local
```bash
# Servidor com hot-reload
uvicorn app.main:app --reload

# Testes
pytest                           # todos
pytest tests/test_services/ -v   # diretório específico
pytest --cov=app --cov-report=html

# Qualidade
black . && isort .
flake8 app/ tests/
mypy app/
```

### Docker (Multi-arch: AMD64/ARM64)
```bash
make dev          # desenvolvimento com hot-reload
make build        # build para plataforma atual
make buildx       # build multi-arch + push
make prod         # produção
```

### Alembic (Migrations)
```bash
alembic revision --autogenerate -m "descricao"
alembic upgrade head
alembic downgrade -1
```

## Arquitetura

### Camadas
```
app/api/v1/endpoints/  → FastAPI routes (entrada)
app/services/          → Lógica de negócio (orquestração)
app/repositories/      → Acesso a dados (SQLAlchemy)
app/models/            → SQLAlchemy ORM models
app/schemas/           → Pydantic (validação request/response)
app/utils/             → Cache, filtros, utilitários
```

### SQLite Configuration (Automática)
`app/core/sqlite_config.py` aplica otimizações automaticamente via event listener em `app/database.py`:
- WAL mode (concorrência leitura/escrita)
- busy_timeout=5000ms (evita "database is locked")
- foreign_keys=ON
- mmap_size=256MB, cache_size=64MB

Não é necessário configurar manualmente - o event listener `@event.listens_for(engine.sync_engine, "connect")` aplica em novas conexões.

### Integração TJDFT
- **Cliente:** `app/services/tjdft_client.py` (httpx async)
- **Endpoint:** `POST https://jurisdf.tjdft.jus.br/api/v1/pesquisa`
- **Paginação:** 0-indexed, máximo 40 resultados por página
- **Limitações:** Apenas acórdãos (2ª instância), sem filtro de data

### Cache
`app/utils/cache.py` - Redis com fallback in-memory LRU (max 1000 entradas). Verifica saúde da conexão Redis automaticamente.

## Variáveis de Ambiente

```bash
DATABASE_URL=sqlite+aiosqlite:///./tjdft.db  # ou postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600
DEBUG=false
CORS_ORIGINS=["http://localhost:3000"]
OPENAI_API_KEY=sk-...  # opcional
```

## Padrões

### Nomenclatura
- Arquivos: `snake_case`
- Classes: `PascalCase`
- Funções/Variáveis: `snake_case`
- Constantes: `UPPER_SNAKE_CASE`
- Privados: prefixo `_`

### Async/Await
Todo o projeto usa async/await. Sessions SQLAlchemy via dependency:
```python
async def endpoint(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Decisao))
```

## Commit Checklist

1. `pytest` passando
2. `black .` e `isort .` aplicados
3. `flake8 app/ tests/` limpo
4. `mypy app/` sem erros
