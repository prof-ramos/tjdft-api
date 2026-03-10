# TJDFT API

> API FastAPI para consulta de jurisprudência do Tribunal de Justiça do Distrito Federal e Territórios

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🎯 Sobre

Esta API fornece uma interface moderna e assíncrona para busca de jurisprudência do TJDFT, com recursos avançados de:

- 🔍 **Busca simples e avançada** com filtros múltiplos
- 📄 **Paginação automática** de resultados
- 💾 **Cache inteligente** com Redis
- 🔄 **Async/await** para alta performance
- 📊 **Análise** de decisões judiciais

## 🚀 Quick Start

```bash
# Clonar repositório
git clone https://github.com/prof-ramos/tjdft-api.git
cd tjdft-api

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar ambiente
cp .env.example .env

# Rodar servidor
uvicorn app.main:app --reload
```

## 📡 Endpoints

### Health Check
```http
GET /health
```

### Busca Simples
```http
GET /api/v1/busca?q=tributário&pagina=1&tamanho=20
```

### Busca com Filtros
```http
GET /api/v1/busca/filtros?q=tributário&relator=Nome&classe=Apelação
```

## 📖 Documentação

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI**: http://localhost:8000/openapi.json

## 🧪 Testes

```bash
# Rodar todos os testes
pytest

# Com cobertura
pytest --cov=app --cov-report=html

# Teste específico
pytest tests/test_services/test_tjdft_client.py -v
```

## 🔧 Desenvolvimento

### Qualidade de Código

```bash
# Formatar
black .
isort .

# Verificar
black --check .
flake8 app/
mypy app/
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

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👨‍💻 Autor

**Gabriel Ramos** - [@prof-ramos](https://github.com/prof-ramos)

---

⭐ Se este projeto foi útil, considere dar uma estrela!
