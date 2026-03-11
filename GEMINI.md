# Gemini Context: TJDFT API

Esta é uma API moderna e assíncrona, construída com **FastAPI**, para busca e análise de jurisprudência do **Tribunal de Justiça do Distrito Federal e Territórios (TJDFT)**.

## 🏗️ Visão Geral do Projeto

- **Propósito**: Interface simplificada e poderosa para a base de dados de acórdãos do TJDFT.
- **Tecnologias Principais**:
  - **Python**: 3.11+
  - **Framework**: FastAPI (0.109+)
  - **Banco de Dados**: SQLAlchemy 2.0 (async) com suporte a SQLite (dev) e PostgreSQL (prod)
  - **Cache**: Redis com fallback em memória
    - **Fallback**: O sistema utiliza cache em memória quando o Redis não está disponível ou inacessível (ex.: ausência/invalidade de `REDIS_URL`, falha de conexão, autenticação rejeitada, timeouts). O cache em memória persiste apenas durante o ciclo de vida do processo, não sendo compartilhado entre instâncias e sendo perdido em reinicializações.
    - **Reconexão**: O sistema tenta reconectar automaticamente ao Redis. Recomenda-se monitoramento de alertas para conexões Redis.
    - **Configuração**: Controlado via variável `REDIS_URL`. Defina `REDIS_URL` vazia ou omitida para usar apenas cache em memória.
  - **Cliente HTTP**: httpx (async)
  - **Migrations**: Alembic
  - **Gerenciador**: `uv` (recomendado)
- **Arquitetura**: Camadas bem definidas (API -> Services -> Repositories -> Models/Schemas).

## 🚀 Comandos Principais (Building & Running)

Este projeto utiliza `uv` para gerenciamento de dependências.

### Configuração Inicial

```bash
# Criar ambiente virtual e instalar dependências
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Configurar variáveis de ambiente
cp .env.example .env

# Variáveis de ambiente principais:
# - DATABASE_URL: URL de conexão do banco de dados (ex: sqlite+aiosqlite:///./tjdft.db ou postgresql+asyncpg://user:pass@host/db)
# - REDIS_URL: URL de conexão Redis (ex: redis://localhost:6379/0). Omitir para usar apenas cache em memória.
# - OPENAI_API_KEY: Chave da API OpenAI para ferramentas de IA
# - SESSION_SECRET: Segredo para sessões e tokens JWT
# - PORT: Porta do servidor (padrão: 8000)
# - LOG_LEVEL: Nível de logging (INFO, DEBUG, WARNING, ERROR)
```

### Execução

```bash
# Rodar migrations
uv run alembic upgrade head

# Iniciar servidor de desenvolvimento
uv run uvicorn app.main:app --reload
```

### Testes e Qualidade

```bash
# Rodar todos os testes com cobertura
uv run pytest --cov=app --cov-report=term-missing

# Meta de cobertura: >= 80% (verifique com --cov-report)

# Verificação de estilo e tipos
uv run black --check .
uv run isort --check .
uv run flake8 app/
uv run mypy app/

# Pre-commit hooks (instalar com: pre-commit install)
# Os seguintes checks rodam automaticamente antes de cada commit:
# - black (formatação)
# - isort (ordenação de imports)
# - flake8 (linting)
# - mypy (type checking)
# - pytest (testes)
```

### Docker

O projeto oferece dois fluxos principais via Docker:

- **Desenvolvimento (`make dev`)** - usa `docker-compose.dev.yml`:
  - **web** (app): Servidor FastAPI com hot-reload (porta 8000)
  - **postgres**: Banco de dados PostgreSQL (porta 5432)
  - **redis**: Cache Redis (porta 6379)
  - **worker**: Processamento background (opcional)
  - Monta volumes locais para habilitar **hot-reload**.
  - Ideal para iteração rápida no código.

- **Produção (`docker compose up -d`)** - usa `docker-compose.yml`:
  - **web** (app): Servidor FastAPI (estático, sem volumes)
  - **postgres**: Banco de dados PostgreSQL
  - **redis**: Cache Redis
  - **worker**: Processamento background
  - **migrations**: Job de migração (roda uma vez na inicialização)
  - Ideal para deploy ou testes de performance.

## 📜 Convenções de Desenvolvimento

### Estrutura de Camadas

- `app/api/v1/endpoints/`: Definição das rotas e documentação FastAPI.
- `app/services/`: Lógica de negócio e orquestração (ex: `busca_service.py`).
- `app/repositories/`: Operações diretas no banco de dados.
- `app/models/`: Modelos SQLAlchemy (definição das tabelas).
- `app/schemas/`: Modelos Pydantic v2 (validação de entrada/saída).
- `app/utils/`: Gerenciador de cache, filtros e processamento de dados.

### Padrões de Código

- **Async/Await**: Toda a cadeia de chamadas (API -> DB -> Cache) deve ser assíncrona.
- **Cache**: Utilize o `CacheManager` em `app/utils/cache.py` para evitar chamadas externas desnecessárias.
- **Nomenclatura de Branches**: Use os prefixos `feature/`, `fix/`, `docs/`, `refactor/`, `test/`.

### Error Handling

- Use `HTTPException` do FastAPI para erros HTTP (ex: `raise HTTPException(status_code=404, detail="...")`).
- Crie exceções customizadas em `app/exceptions.py` para erros de domínio.
- Adicione um global exception handler em `app/api/v1/endpoints/` para mapear erros de domínio para respostas HTTP.
- Exemplo de estrutura recomendada:

```python
# app/exceptions.py
class EntityNotFoundException(Exception):
    def __init__(self, entity: str, identifier: str):
        self.entity = entity
        self.identifier = identifier
        super().__init__(f"{entity} não encontrado: {identifier}")

# app/api/deps.py (handler)
from fastapi import Request, status
from fastapi.responses import JSONResponse

async def global_exception_handler(request: Request, exc: EntityNotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)}
    )
```

### Logging

- Use `logging` (stdlib) ou `structlog` para logging estruturado.
- Formato recomendado: JSON estruturado com campos (level, timestamp, message, context).
- Use os níveis corretos: `DEBUG` (detalhes de execução), `INFO` (eventos normais), `WARNING` (atenção), `ERROR` (erros).
- Adicione logging em pontos críticos: `CacheManager` em `app/utils/cache.py`, repositories, e serviços.
- Exemplo:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("busca_realizada", termo=termo, resultados=len(resultados))
logger.error("falha_busca", erro=str(exc), termo=termo)
```

### Autenticação

- Use OAuth2 com JWT para autenticação ou API Keys.
- Dependências de autenticação ficam em `app/api/deps.py` (ex: `get_current_user`).
- Utilities de verificação de token em `app/utils/security.py`.
- Proteja endpoints com dependências: `@router.get("/", dependencies=[Depends(get_current_user)])`.

### Testing

- Use `pytest` com `pytest-asyncio` para testes assíncronos.
- Fixtures em `tests/fixtures/` ou no mesmo arquivo `conftest.py`.
- Nomenclatura: `test_*.py`, classes `Test*`, funções `test_*`.
- Use mocks/factories para repositories (`app.repositories`).
- Testes de integração em `tests/test_api/` para testar endpoints completos.
- Exemplo de fixture:

```python
# tests/fixtures/database.py
@pytest.fixture
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

## 📡 Endpoints Relevantes

### POST /api/v1/busca/
Busca principal de jurisprudência no TJDFT.

**Parâmetros obrigatórios**:
- `termo` (string): Termo de busca na ementa ou inteiro teor
- `ano` (integer, opcional): Ano do acórdão
- `numero` (string, opcional): Número do processo
- `classe` (string, opcional): Classe processual (ex: "Apelação", "Agravo")
- `relator` (string, opcional): Nome do relator

**Autenticação**: Não requer autenticação (público).

**Rate Limiting**: 60 requisições por minuto por IP.

**Exemplo de requisição**:
```json
{
  "termo": "indenização",
  "ano": 2024,
  "classe": "Apelação",
  "limit": 10
}
```

**Exemplo de resposta**:
```json
{
  "items": [
    {
      "uuid_tjdft": "0700000-00.2024.8.07.0001",
      "ementa": "Ementa do acórdão...",
      "inteiro_teor_url": "https://...",
      "data_publicacao": "2024-01-15",
      "relator": "Desembargador Fulano"
    }
  ],
  "total": 1,
  "page": 1
}
```

### GET /health
Status de saúde da API. Retorna o status de conexão com banco de dados e Redis.

**Autenticação**: Não requer autenticação.

**Exemplo de resposta**:
```json
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected"
}
```

### GET /docs
Documentação interativa Swagger (OpenAPI). Acesse no navegador para testar os endpoints.

**Autenticação**: Não requer autenticação.

## 🤖 Suporte a MCP (Model Context Protocol)

O projeto inclui suporte nativo a MCP em `app/mcp/`, permitindo que agentes de IA utilizem as ferramentas de busca do TJDFT diretamente no terminal ou em clientes compatíveis.
