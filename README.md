# TJDFT API

> API FastAPI para consulta de jurisprudência do Tribunal de Justiça do Distrito Federal e Territórios

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-gabrielramosprof%2Ftjdft--latest-blue.svg)](https://hub.docker.com/r/gabrielramosprof/tjdft-api)

## 🎯 Sobre

Esta API fornece uma interface moderna e assíncrona para busca de jurisprudência do TJDFT, com recursos avançados de:

- 🔍 **Busca simples e avançada** com filtros múltiplos
- 📄 **Paginação automática** de resultados
- 💾 **Cache inteligente** com Redis
- 🔄 **Async/await** para alta performance
- 📊 **Análise** de decisões judiciais
- 🐳 **Docker multi-arch** (AMD64/ARM64) para deploy facilitado

## 🚀 Quick Start

### Local (Python)

```bash
# Clonar repositório
git clone https://github.com/prof-ramos/tjdft-api.git
cd tjdft-api

# Criar e ativar ambiente virtual
uv venv .venv
source .venv/bin/activate

# Instalar dependências
uv pip install -e ".[dev]"

# Configurar ambiente
cp .env.example .env

# Rodar servidor
uv run uvicorn app.main:app --reload
```

### Docker (Recomendado)

```bash
# Desenvolvimento
make dev

# Produção
docker compose up -d

# Swarm + Traefik
./deploy-swarm.sh 1.0.0
```

## 🐳 Docker

A imagem Docker está disponível em [DockerHub](https://hub.docker.com/r/gabrielramosprof/tjdft-api):

```bash
docker pull gabrielramosprof/tjdft-api:latest

# Executar
docker run -p 8000:8000 -e DATABASE_URL="sqlite+aiosqlite:////app/data/tjdft.db" gabrielramosprof/tjdft-api:latest
```

**Multi-arquitetura:** `linux/amd64`, `linux/arm64`

## 📡 Endpoints

### Root
```http
GET /
```

### Health Check
```http
GET /health
```

### Busca de decisões
```http
POST /api/v1/busca/
```

Use `application/json` no corpo e, opcionalmente, os query params
`excluir_turmas_recursais` e `apenas_ativos`.

## 🧪 Exemplos de Uso com curl

Após iniciar o servidor com `uv run uvicorn app.main:app --reload`:

```bash
# Health check
curl http://localhost:8000/health

# Busca básica
curl -X POST "http://localhost:8000/api/v1/busca/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tributário",
    "pagina": 1,
    "tamanho": 10
  }'

# Busca com filtros e query params opcionais
curl -X POST "http://localhost:8000/api/v1/busca/?apenas_ativos=true" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tributário",
    "filtros": {
      "relator": "desembargador-faustolo",
      "classe": "APC",
      "orgao_julgador": "6CC"
    },
    "pagina": 1,
    "tamanho": 5
  }'

# Resposta formatada com jq
curl -s -X POST "http://localhost:8000/api/v1/busca/" \
  -H "Content-Type: application/json" \
  -d '{"query":"tributário","pagina":1,"tamanho":5}' | jq .
```

## 📖 Documentação

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI**: http://localhost:8000/openapi.json
- **Referência da API do projeto**: [docs/api_reference.md](docs/api_reference.md)
- **API pública original do TJDFT usada como fonte de dados**: [docs/tjdft_api.md](docs/tjdft_api.md)
- **MCP (quickstart)**: [docs/mcp/quickstart.md](docs/mcp/quickstart.md)
- **MCP (configuração de exemplo)**: [docs/mcp/example.mcp.json](docs/mcp/example.mcp.json)

## 🧪 Testes

```bash
# Rodar todos os testes
uv run pytest

# Com cobertura
uv run pytest --cov=app --cov-report=html

# Teste específico
uv run pytest tests/test_services/test_tjdft_client.py -v
```

## 🔧 Desenvolvimento

### Qualidade de Código

```bash
# Formatar
uv run black .
uv run isort .

# Verificar
uv run black --check .
uv run flake8 app/
uv run mypy app/
```

### Estrutura do Projeto

```
tjdft-api/
├── app/
│   ├── api/              # Endpoints FastAPI
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Lógica de negócio
│   ├── repositories/     # Acesso a dados
│   └── utils/            # Utilitários (cache, filtros)
├── tests/                # Testes
└── CLAUDE.md            # Documentação para Claude Code
```

## ⚙️ Variáveis de Ambiente

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./tjdft.db
# Para PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost/tjdft_db

# Cache
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600

# API
DEBUG=false
```

## 🗄️ Migrations com Alembic

Este projeto usa Alembic para gerenciar migrations do banco de dados, com suporte a PostgreSQL e SQLite.

### Comandos Básicos

```bash
# Criar uma nova migration (autogenerate a partir dos models)
alembic revision --autogenerate -m "Descrição da mudança"

# Aplicar migrations (upgrade para a versão mais recente)
alembic upgrade head

# Reverter a última migration
alembic downgrade -1

# Reverter para uma versão específica
alembic downgrade <revision_id>

# Ver o histórico de migrations
alembic history

# Ver a versão atual
alembic current
```

### Suporte a Banco de Dados

**SQLite (padrão - desenvolvimento):**
```bash
DATABASE_URL=sqlite+aiosqlite:///./tjdft.db
```

**PostgreSQL (produção):**
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tjdft_db
```

As migrations funcionam automaticamente com ambos os bancos, usando o driver apropriado.

## 📦 Stack Tecnológico

| Componente | Tecnologia |
|------------|-----------|
| **Framework** | FastAPI 0.109+ |
| **ORM** | SQLAlchemy 2.0+ |
| **Validação** | Pydantic v2 |
| **HTTP Client** | httpx (async) |
| **Cache** | Redis |
| **Testes** | pytest |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **Deploy** | Docker Swarm + Traefik |

## 🚀 Deploy

### Docker Swarm + Portainer

1. **Build e push:**
```bash
make buildx
# ou
./deploy-swarm.sh 1.0.0
```

2. **No Portainer:**
   - Stacks → Add Stack
   - Nome: `tjdft`
   - Upload `docker-compose.swarm.yml`
   - **IMPORTANTE:** Altere `api.seu-dominio.com.br` para seu domínio real
   - Deploy

3. **Traefik vai configurar automaticamente:**
   - HTTP → HTTPS redirect
   - SSL automático (LetsEncrypt)
   - Rate limiting
   - Health checks

**Deploy manual via CLI:**
```bash
docker stack deploy -c docker-compose.swarm.yml tjdft
```

### Variáveis de Importante

Edite `docker-compose.swarm.yml` antes do deploy:

```yaml
# DOMÍNIO - ALTERAR ESTE!
- "traefik.http.routers.tjdft-api-secure.rule=Host(`api.seu-dominio.com.br`)"
- "traefik.http.routers.tjdft-api.rule=Host(`api.seu-dominio.com.br`)"

# CORS_ORIGINS
- CORS_ORIGINS=["https://seu-dominio.com.br"]
```

### Informações Completas de Deploy

Veja [DEPLOYMENT.md](DEPLOYMENT.md) para:
- Pré-requisitos do cluster
- Configuração do Traefik
- Backup e restore
- Troubleshooting

## 🤝 Contribuindo

### Padrão de Nomenclatura de Branches

| Prefixo | Uso | Exemplo |
|---------|-----|---------|
| `feature/` | Novas funcionalidades | `feature/add-export-pdf` |
| `fix/` | Correções de bugs | `fix/async-sqlite-date-validation` |
| `docs/` | Documentação | `docs/update-readme-api-examples` |
| `refactor/` | Refatoração de código | `refactor/extract-cache-service` |
| `test/` | Testes | `test/add-busca-integration-tests` |
| `chore/` | Manutenção (deps, configs) | `chore/update-dependencies` |
| `hotfix/` | Correções urgentes em produção | `hotfix/fix-auth-bypass` |

**Convenção:** `{tipo}/{descrição-curta-em-kebab-case}`

### Fluxo de Contribuição

1. Fork o projeto
2. Crie uma branch seguindo o padrão (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👨‍💻 Autor

**Gabriel Ramos** - [@prof-ramos](https://github.com/prof-ramos)

---

⭐ Se este projeto foi útil, considere dar uma estrela!
