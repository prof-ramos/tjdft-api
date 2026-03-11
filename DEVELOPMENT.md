# Guia do Desenvolvedor

Guia completo para desenvolvimento da TJDFT API.

## 1. Configuração do Ambiente

### Pré-requisitos

- Python 3.11+
- Git
- Docker (opcional, para containerização)
- Redis (opcional, para cache)

### Passo a Passo

```bash
# 1. Clone o repositório
git clone https://github.com/prof-ramos/tjdft-api.git
cd tjdft-api

# 2. Crie o ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Instale as dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env conforme necessário

# 5. Execute as migrations (se usando PostgreSQL)
alembic upgrade head

# 6. Inicie o servidor
uvicorn app.main:app --reload
```

### Verificação

Acesse http://localhost:8000/docs para ver a documentação interativa da API.

---

## 2. Estrutura do Projeto

### Visão Geral

```
tjdft-api/
├── app/                        # Aplicação principal
│   ├── api/v1/endpoints/       # Endpoints FastAPI
│   ├── core/                   # Módulos centrais
│   │   └── sqlite_config.py    # Configuração SQLite (WAL, pragmas)
│   ├── models/                 # SQLAlchemy ORM
│   ├── schemas/                # Pydantic (validação)
│   ├── repositories/           # Acesso a dados
│   ├── services/               # Lógica de negócio
│   ├── utils/                  # Utilitários (cache, filtros)
│   ├── main.py                 # Entry point FastAPI
│   ├── config.py               # Configurações (pydantic-settings)
│   └── database.py             # Conexão + session factory
├── tests/                      # Testes
│   ├── test_api/               # Testes de endpoints
│   ├── test_services/          # Testes de serviços
│   ├── test_repositories/      # Testes de repositórios
│   └── e2e/                    # Testes end-to-end
├── alembic/                    # Migrations
├── docs/                       # Documentação adicional
├── Dockerfile                  # Multi-arch build
├── docker-compose.yml          # Compose local
├── docker-compose.swarm.yml    # Swarm stack (produção)
├── Makefile                    # Comandos Docker úteis
└── pyproject.toml              # Config pytest, black, mypy
```

### Camadas da Arquitetura

| Camada | Responsabilidade | Exemplo |
|--------|-----------------|---------|
| **API** | Receber requisições HTTP, retornar JSON | `busca.py` |
| **Service** | Orquestrar lógica, coordenar repositories | `busca_service.py` |
| **Repository** | Acessar banco de dados, executar queries | `decisao_repo.py` |
| **Model** | Definir schema do banco | `decisao.py` |
| **Schema** | Validar request/response Pydantic | `decisao.py` |
| **Utils** | Funcionalidades transversais | `cache.py` |

---

## 3. Fluxo de Trabalho de Desenvolvimento

### Branch Convention

```
feature/     Nova funcionalidade
fix/         Correção de bug
docs/        Documentação
refactor/    Refatoração
test/        Testes
chore/       Manutenção (deps, configs)
```

### Ciclo de Desenvolvimento

```bash
# 1. Crie uma branch
git checkout -b feature/nova-feature

# 2. Faça as alterações
# ... edite os arquivos ...

# 3. Formate e verifique o código
black . && isort .
flake8 app/ tests/
mypy app/

# 4. Execute os testes
pytest

# 5. Commit
git add .
git commit -m "feat: descrição da mudança"

# 6. Push e PR
git push origin feature/nova-feature
```

### Adicionando um Novo Endpoint

1. **Schema** (`app/schemas/novo_schema.py`)
   ```python
   from pydantic import BaseModel

   class NovoRequest(BaseModel):
       campo: str

   class NovoResponse(BaseModel):
       resultado: str
   ```

2. **Repository** (`app/repositories/novo_repo.py`)
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select

   async def buscar_dados(session: AsyncSession):
       result = await session.execute(select(Model))
       return result.scalars().all()
   ```

3. **Service** (`app/services/novo_service.py`)
   ```python
   async def processar_dados(session: AsyncSession):
       dados = await buscar_dados(session)
       # lógica aqui
       return dados
   ```

4. **Endpoint** (`app/api/v1/endpoints/novo.py`)
   ```python
   from fastapi import APIRouter, Depends
   from app.database import get_session
   from app.schemas.novo_schema import NovoRequest, NovoResponse

   router = APIRouter()

   @router.post("/novo", response_model=NovoResponse)
   async def criar_novo(
       req: NovoRequest,
       session: AsyncSession = Depends(get_session)
   ):
       resultado = await processar_dados(session)
       return NovoResponse(resultado=resultado)
   ```

5. **Registrar** (`app/api/v1/router.py` ou `main.py`)
   ```python
   from app.api.v1.endpoints import novo
   api_router.include_router(novo.router, prefix="/novo", tags=["novo"])
   ```

6. **Testes** (`tests/test_api/test_novo.py`)

---

## 4. Abordagem de Testes

### Pirâmide de Testes

```
       /\
      /  \        E2E (poucos, lentos)
     /____\
    /      \      Integração
   /        \     (médios, moderados)
  /__________\
 /            \  Unitários (muitos, rápidos)
/______________\
```

### Tipos de Teste

| Tipo | Local | Exemplo |
|------|-------|---------|
| **Unitário** | `tests/test_utils/` | Testar função isolada |
| **Integração** | `tests/test_services/` | Testar service + repository |
| **API** | `tests/test_api/` | Testar endpoint com TestClient |
| **E2E** | `tests/e2e/` | Testar fluxo completo |

### Executando Testes

```bash
# Todos os testes
pytest

# Com cobertura
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Teste específico
pytest tests/test_services/test_tjdft_client.py -v

# Teste por marcador
pytest -m unit        # apenas unitários
pytest -m integration # apenas integração
pytest -m e2e         # apenas e2e

# Paralelo (mais rápido)
pytest -n auto
```

### Estrutura de Teste

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_busca_simples():
    """Testa busca simples por texto."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/busca?q=tributario")
        assert response.status_code == 200
        data = response.json()
        assert "resultados" in data
```

### Fixtures Comuns

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.database import get_session, Base

@pytest.fixture
async def session():
    """Sessão de teste com banco isolado."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
```

---

## 5. Solução de Problemas

### Problema: "Database is locked"

**Causa:** SQLite em modo padrão bloqueia durante escritas.

**Solução:** O projeto já usa WAL mode automaticamente. Se persistir:

```bash
# Verificar se o arquivo -wal e -shm existem
ls -la *.db*

# Se houver processos órfãos, encerrar
# Verificar conexões não fechadas no código
```

### Problema: Redis connection refused

**Causa:** Redis não está rodando.

**Solução:**

```bash
# Iniciar Redis
docker run -p 6379:6379 redis:7-alpine

# Ou usar docker-compose
docker compose up -d redis

# O cache faz fallback automático para in-memory
```

### Problema: ImportError ao rodar testes

**Causa:** PYTHONPATH não configurado ou módulo não instalado.

**Solução:**

```bash
# Instalar em modo editable
pip install -e .

# Ou definir PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Problema: Type hints errados no mypy

**Sausa:** Falta de importação ou configuração.

**Solução:**

```bash
# Verificar mypy.ini ou pyproject.toml
# Adicionar imports explícitos
from typing import Optional, List, Dict, Any
```

### Problema: Docker build falha

**Causa:** Cache do Docker ou dependências quebradas.

**Solução:**

```bash
# Limpar cache e rebuild
docker builder prune -a
docker compose build --no-cache

# Verificar logs detalhados
docker compose up --build
```

### Problema: Migração Alembic falha

**Causa:** Banco fora de sync com as migrations.

**Solução:**

```bash
# Verificar versão atual
alembic current

# Ver histórico
alembic history

# Forçar para versão específica (CUIDADO em prod)
alembic stamp head

# Recriar banco (dev apenas)
dropdb tjdft_db && createdb tjdft_db
alembic upgrade head
```

### Debugging com logs

```python
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Variável: %s", variavel)
logger.info("Processando request")
logger.error("Erro: %s", e)
```

### Verificando health

```bash
# Health check
curl http://localhost:8000/health

# Ver resposta esperada: {"status": "healthy"}
```

---

## 6. Referências Rápidas

| Comando | Propósito |
|---------|-----------|
| `uvicorn app.main:app --reload` | Servidor dev |
| `pytest --cov=app` | Testes + cobertura |
| `black . && isort .` | Format código |
| `flake8 app/ tests/` | Lint |
| `mypy app/` | Type check |
| `alembic revision --autogenerate` | Nova migration |
| `make dev` | Docker dev |
| `make buildx` | Docker multi-arch |

---

## 7. Recursos Adicionais

- **FastAPI:** https://fastapi.tiangolo.com/
- **SQLAlchemy 2.0:** https://docs.sqlalchemy.org/en/20/
- **Pydantic v2:** https://docs.pydantic.dev/latest/
- **pytest-asyncio:** https://pytest-asyncio.readthedocs.io/
- **SQLite Best Practices:** Veja `app/core/sqlite_config.py`
