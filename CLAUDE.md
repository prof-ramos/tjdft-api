# CLAUDE.md - TJDFT API

Este arquivo fornece orientação para o Claude Code ao trabalhar com este repositório.

## Visão Geral do Projeto

**TJDFT API** é uma API FastAPI para consulta de jurisprudência do Tribunal de Justiça do Distrito Federal e Territórios. O projeto fornece uma interface moderna para busca de decisões judiciais com recursos avançados de filtragem, cache e paginação.

### Stack Tecnológico
- **Python 3.11+** - Linguagem principal
- **FastAPI 0.109+** - Framework web assíncrono
- **SQLAlchemy 2.0+** - ORM para banco de dados
- **Pydantic v2** - Validação de dados
- **httpx** - Cliente HTTP assíncrono
- **pytest** - Framework de testes

## Estrutura do Projeto

```
tjdft-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicação FastAPI principal
│   ├── config.py            # Configurações (pydantic-settings)
│   ├── database.py          # Configuração do banco de dados
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/   # Endpoints da API
│   ├── core/                # Módulos centrais
│   │   └── config.py        # Configurações centrais
│   ├── models/              # SQLAlchemy models
│   │   ├── consulta.py      # Histórico de consultas
│   │   └── decisao.py       # Decisões judiciais
│   ├── schemas/             # Pydantic schemas
│   │   ├── consulta.py      # Schemas de consulta
│   │   ├── decisao.py       # Schemas de decisão
│   │   └── analise.py       # Schemas de análise
│   ├── repositories/        # Camada de acesso a dados
│   ├── services/            # Lógica de negócio
│   │   └── tjdft_client.py # Cliente HTTP para API do TJDFT
│   └── utils/               # Utilitários
│       ├── cache.py         # Gerenciador de cache
│       └── filtros.py       # Filtros de busca
├── tests/
│   ├── test_main.py         # Testes principais
│   ├── test_api/            # Testes de endpoints
│   ├── test_repositories/   # Testes de repositórios
│   └── test_services/       # Testes de serviços
├── requirements.txt         # Dependências de produção
├── requirements-dev.txt     # Dependências de desenvolvimento
└── pyproject.toml          # Configuração do projeto
```

## Comandos de Desenvolvimento

### Ambiente Virtual
```bash
# Criar ambiente virtual
python -m venv venv

# Ativar (Linux/Mac)
source venv/bin/activate

# Ativar (Windows)
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Servidor de Desenvolvimento
```bash
# Iniciar servidor com hot-reload
uvicorn app.main:app --reload

# Iniciar em porta específica
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Ver documentação
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

### Testes
```bash
# Rodar todos os testes
pytest

# Rodar com cobertura
pytest --cov=app --cov-report=html

# Rodar teste específico
pytest tests/test_main.py -v

# Rodar testes de um diretório
pytest tests/test_services/ -v
```

### Qualidade de Código
```bash
# Formatar código (Black)
black .

# Verificar formatação
black --check .

# Ordenar imports (isort)
isort .

# Verificar imports
isort --check-only .

# Linting (Flake8)
flake8 app/ tests/

# Type checking (MyPy)
mypy app/
```

## Padrões do Projeto

### Convenções de Nomenclatura
- **Arquivos/Módulos**: `snake_case` (ex: `tjdft_client.py`)
- **Classes**: `PascalCase` (ex: `TJDFTClient`)
- **Funções/Variáveis**: `snake_case` (ex: `buscar_simples`)
- **Constantes**: `UPPER_SNAKE_CASE` (ex: `BASE_URL`)
- **Métodos privados**: prefixo `_` (ex: `_build_cache_key`)

### Padrões de Código

#### Type Hints
```python
from typing import Optional, List, Dict, Any

async def buscar_simples(
    self,
    query: str,
    pagina: int = 1,
    tamanho: int = 20,
) -> Dict[str, Any]:
    """Busca simples por texto na API do TJDFT."""
    ...
```

#### Pydantic Models
```python
from pydantic import BaseModel, Field

class ConsultaRequest(BaseModel):
    """Modelo de requisição de consulta."""
    query: str = Field(..., min_length=1, description="Termo de busca")
    pagina: int = Field(1, ge=1, description="Número da página")
    tamanho: int = Field(20, ge=1, le=100, description="Resultados por página")
```

#### SQLAlchemy Models
```python
from sqlalchemy import Column, String, DateTime
from app.database import Base

class Consulta(Base):
    """Model para histórico de consultas."""
    __tablename__ = "consultas"
    id = Column(String, primary_key=True)
    query = Column(String, nullable=False)
```

### Padrões Assíncronos

O projeto usa **async/await** extensivamente:

```python
import asyncio
from httpx import AsyncClient

async def buscar_dados() -> Dict[str, Any]:
    """Função assíncrona para buscar dados."""
    async with AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

## Integração com API TJDFT

### TJDFTClient
O cliente principal para interagir com a API do TJDFT está em `app/services/tjdft_client.py`:

```python
from app.services.tjdft_client import TJDFTClient
from app.utils.cache import CacheManager

# Uso
cache = CacheManager()
async with TJDFTClient(cache) as client:
    results = await client.buscar_simples("tributário")
    print(results)
```

### Métodos Disponíveis
- `buscar_simples(query, pagina, tamanho)` - Busca simples
- `buscar_com_filtros(query, **filtros)` - Busca com filtros avançados
- `buscar_todas_paginas(query, max_paginas)` - Paginação automática
- `get_metadata()` - Metadados da API (filtros disponíveis)

### Cache
O projeto usa Redis para cache com TTL configurável:

```python
from app.utils.cache import CacheManager

cache = CacheManager()
cache.set(key, value, ttl=3600)
result = cache.get(key)
```

## Configuração

### Variáveis de Ambiente
```bash
# .env
DATABASE_URL=sqlite:///./tjdft.db
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600
OPENAI_API_KEY=sk-... # opcional
DEBUG=false
```

### Arquivo de Configuração
O projeto usa `pydantic-settings` em `app/config.py`:

```python
from app.config import get_settings

settings = get_settings()
print(settings.app_name)
```

## Guias Específicos

### Adicionar Novo Endpoint

1. Criar Pydantic schema em `app/schemas/`
2. Adicionar endpoint em `app/api/v1/endpoints/`
3. Adicionar testes em `tests/test_api/`
4. Documentar com docstrings

### Adicionar Nova Feature

1. Criar model em `app/models/` (se necessário)
2. Criar repository em `app/repositories/`
3. Criar service em `app/services/`
4. Criar schema em `app/schemas/`
5. Adicionar endpoint em `app/api/v1/endpoints/`
6. Escrever testes

### Tratamento de Erros

```python
from app.services.tjdft_client import (
    TJDFTClientError,
    TJDFTConnectionError,
    TJDFTTimeoutError,
    TJDFTAPIError,
)

try:
    results = await client.buscar_simples(query)
except TJDFTConnectionError as e:
    # Erro de conexão
    pass
except TJDFTTimeoutError as e:
    # Timeout
    pass
except TJDFTAPIError as e:
    # Erro da API
    pass
```

## Checklist de Commits

Antes de commitar:

1. [ ] Testes passando: `pytest`
2. [ ] Código formatado: `black .`
3. [ ] Imports ordenados: `isort .`
4. [ ] Linting OK: `flake8 app/ tests/`
5. [ ] Type check OK: `mypy app/`
6. [ ] Documentação atualizada

## Referências Úteis

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/en/20/
- **Pydantic v2**: https://docs.pydantic.dev/latest/
- **httpx**: https://www.python-httpx.org/
- **pytest**: https://docs.pytest.org/

## Notas Específicas do Projeto

- O projeto usa **PostgreSQL** em produção (JSONB para filtros)
- **Redis** é usado para cache de respostas da API
- **OpenAI** pode ser usado para análise de decisões (opcional)
- A API do TJDFT tem rate limiting - usar cache sempre que possível
- Paginação automática é suportada via `buscar_todas_paginas()`
