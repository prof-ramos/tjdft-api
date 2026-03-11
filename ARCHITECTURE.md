# Architecture Overview

This document serves as a critical, living template designed to equip agents with a rapid and comprehensive understanding of the codebase's architecture, enabling efficient navigation and effective contribution from day one. Update this document as the codebase evolves.

## 1. Project Structure

This section provides a high-level overview of the project's directory and file structure, categorized by architectural layer or major functional area.

```
tjdft-api/
├── app/                         # Main application source code
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Configuration (pydantic-settings)
│   ├── database.py              # Database connection & session management
│   ├── core/                    # Core modules
│   │   └── sqlite_config.py     # SQLite PRAGMA configuration (WAL, timeouts, etc.)
│   ├── api/                     # API layer (endpoints)
│   │   └── v1/
│   │       └── endpoints/
│   │           └── busca.py     # Search endpoints
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── decisao.py           # Cached judicial decisions
│   │   └── consulta.py          # Search query history
│   ├── schemas/                 # Pydantic schemas (request/response)
│   │   ├── decisao.py           # Decision schemas
│   │   ├── consulta.py          # Search request/response schemas
│   │   └── analise.py           # Analysis schemas
│   ├── services/                # Business logic layer
│   │   ├── tjdft_client.py      # Async HTTP client for TJDFT API
│   │   ├── busca_service.py     # Search orchestration service
│   │   ├── ai_service.py        # AI analysis (OpenAI integration)
│   │   └── estatisticas_service.py
│   ├── repositories/            # Data access layer
│   │   ├── decisao_repo.py      # Decision repository
│   │   └── consulta_repo.py     # Consulta repository
│   └── utils/                   # Utility modules
│       ├── cache.py             # Unified cache manager (Redis + in-memory)
│       ├── filtros.py           # Search filter utilities
│       └── enrichment.py        # Data enrichment utilities
│   └── mcp/                     # MCP (Model Context Protocol) server
│       ├── __main__.py          # Entry point (python -m app.mcp)
│       ├── server.py            # FastMCP server + lifespan
│       ├── runtime.py           # MCPRuntime (cache, DB sessions, TJDFT client, AI)
│       ├── constants.py         # Enums (ResponseFormat, etc.)
│       ├── errors.py            # Error mapping to MCP error types
│       ├── formatters.py        # Response formatting (markdown/JSON)
│       ├── schemas.py           # Pydantic input schemas for tools
│       └── tools/               # MCP tools implementation
│           ├── search_tools.py  # tjdft_search_decisions, tjdft_get_metadata
│           ├── history_tools.py # tjdft_get_consulta, tjdft_list_history
│           └── ai_tools.py      # tjdft_ai_summarize, tjdft_ai_extract_theses
├── tests/                       # Test suite
│   ├── test_api/                # API endpoint tests
│   ├── test_services/           # Service layer tests
│   └── test_repositories/       # Repository tests
├── alembic/                     # Database migrations
├── data/                        # Static data files
│   └── referencia.json          # Reference data for filters
├── docs/                        # Additional documentation
├── .env.example                 # Environment variables template
├── pyproject.toml               # Project configuration
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── CLAUDE.md                    # Claude Code project instructions
└── README.md                    # Project overview
```

## 2. High-Level System Diagram

```
[Client/User]        [AI Agent (MCP Client)]
        |                       |
        v                       v
[FastAPI Application]    [MCP Server (stdio)]
        |                       |
        +--[Cache Manager]<-----+
               |
               v
        [Redis / In-Memory]
        ^
        |
[TJDFTClient] -- (cache lookup)
        |
        v
[External API: TJDFT Jurisprudence]
        |
        v (responses)
[TJDFTClient] --> [BuscaService] --> [API Endpoints]
                                              |
                                              v
                                         [Response]
```

**Data Flow:**
1. Client sends search request to FastAPI endpoint (or AI agent via MCP)
2. `BuscaService` (or MCP tool) checks cache for existing results
3. On cache miss, `TJDFTClient` makes HTTP request to TJDFT API
4. Response is cached and returned to client/agent
5. Search history is logged to database via repository layer

## 3. Core Components

### 3.1. FastAPI Application

**Name:** TJDFT API Web Service

**Description:** Main FastAPI application providing REST endpoints for searching TJDFT jurisprudence. Handles CORS, dependency injection, and request routing.

**Technologies:** FastAPI 0.109+, Uvicorn, Pydantic v2

**Deployment:** Development (local), Production (configurable)

**Key Responsibilities:**
- HTTP request/response handling
- Dependency injection (database sessions, cache)
- CORS middleware configuration
- API documentation (Swagger/ReDoc)

**Entry Point:** `app/main.py`

### 3.2. Services Layer

#### 3.2.1. TJDFTClient

**Name:** TJDFT API HTTP Client

**Description:** Async HTTP client for communicating with the external TJDFT jurisprudence API. Handles retries, timeouts, and response normalization.

**Technologies:** httpx (async), asyncio

**Key Features:**
- Retry logic with exponential backoff (MAX_RETRIES=3)
- Configurable timeouts (connect: 10s, total: 30s)
- Cache integration via CacheManager
- Response normalization

**Methods:**
- `buscar_simples(query, pagina, tamanho)` - Simple text search
- `buscar_com_filtros(...)` - Advanced search with filters
- `buscar_todas_paginas(...)` - Automatic pagination
- `get_metadata()` - Filter metadata (relatores, classes, órgãos)

**Location:** `app/services/tjdft_client.py`

#### 3.2.2. BuscaService

**Name:** Search Orchestration Service

**Description:** Orchestrates search operations, coordinating between cache, TJDFT client, and database logging.

**Technologies:** Python async/await, SQLAlchemy

**Key Responsibilities:**
- Cache management
- Search query execution
- Result enrichment
- Search history logging

**Location:** `app/services/busca_service.py`

#### 3.2.3. AIService

**Name:** AI Analysis Service (Optional)

**Description:** Provides AI-powered analysis of judicial decisions using OpenAI API.

**Technologies:** OpenAI SDK

**Key Features:**
- Decision summarization
- Relevance analysis
- Key term extraction

**Location:** `app/services/ai_service.py`

### 3.3. Repositories Layer

#### 3.3.1. DecisaoRepository

**Name:** Decision Repository

**Description:** Data access layer for judicial decision cache.

**Technologies:** SQLAlchemy 2.0 async

**Location:** `app/repositories/decisao_repo.py`

#### 3.3.2. ConsultaRepository

**Name:** Consulta Repository

**Description:** Data access layer for search history.

**Technologies:** SQLAlchemy 2.0 async

**Location:** `app/repositories/consulta_repo.py`

### 3.4. Utilities

#### 3.4.1. CacheManager

**Name:** Unified Cache Manager

**Description:** Thread-safe cache with Redis backend and automatic in-memory fallback.

**Technologies:** redis-py, threading, collections.OrderedDict

**Key Features:**
- Redis with lazy connection checking
- In-memory LRU fallback (max 1000 entries)
- TTL expiration support
- Thread-safe singleton pattern
- Connection health monitoring

**Location:** `app/utils/cache.py`

**Cache Key Pattern:** `{prefix}:{type}:{hash}`

### 3.5. MCP Server

**Name:** TJDFT MCP Server

**Description:** Model Context Protocol (MCP) server exposing TJDFT jurisprudence search as tools for AI agents. Implements FastMCP with stdio transport.

**Technologies:** FastMCP, Pydantic v2

**Key Features:**
- Search tools: `tjdft_search_decisions`, `tjdft_get_metadata`, `tjdft_search_all_pages`
- History tools: `tjdft_get_consulta`, `tjdft_list_history`, `tjdft_find_similar_decisions`
- AI tools (optional): `tjdft_ai_summarize`, `tjdft_ai_extract_theses`, `tjdft_ai_compare_decisions`
- Unified runtime with cache, DB sessions, TJDFT client, and AI service
- Response formatting: markdown (default) or JSON

**Entry Point:** `app/mcp/__main__.py` (execute via `python -m app.mcp`)

**Documentation:** See [MCP Implementation Guide](docs/mcp/implementation.md) for complete details.

## 4. Data Stores

### 4.1. Primary Database

**Name:** Application Database

**Type:** SQLite (development), PostgreSQL (production)

**Purpose:** Persistent storage for search history and cached decisions.

**Key Tables:**
- `decisoes` - Cached judicial decisions
- `consultas` - Search query history

**Connection String Format:**
- Dev: `sqlite+aiosqlite:///./tjdft.db`
- Prod: `postgresql+asyncpg://user:password@localhost:5432/tjdft_db`

**ORM:** SQLAlchemy 2.0 async

**Migrations:** Alembic

**SQLite Configuration (Best Practices):**
The application applies SQLite optimizations automatically via `app/core/sqlite_config.py`:

| PRAGMA | Value | Purpose |
|--------|-------|---------|
| `journal_mode` | `WAL` | Write-Ahead Logging for better concurrency |
| `busy_timeout` | `5000 ms` | Wait time for locked database |
| `foreign_keys` | `ON` | Enforce foreign key constraints |
| `mmap_size` | `256 MB` | Memory-mapped I/O for faster reads |
| `synchronous` | `NORMAL` | Balance safety vs performance |
| `cache_size` | `-64000` | 64MB negative cache (in-memory) |

These settings are applied via SQLAlchemy event listener on new connections.

### 4.2. Cache Layer

**Name:** Redis Cache

**Type:** Redis (with in-memory fallback)

**Purpose:** Caching API responses to reduce external calls and improve latency.

**Configuration:**
- URL: `redis://localhost:6379` (configurable via REDIS_URL)
- Default TTL: 3600 seconds (1 hour)
- Prefix: `tjdft`

**Fallback:** In-memory LRU cache when Redis unavailable

## 5. External Integrations / APIs

### TJDFT Jurisprudence API

**Service Name:** TJDFT Jurisprudence Search

**Purpose:** External API for searching judicial decisions (acórdãos) from the Tribunal de Justiça do Distrito Federal e Territórios.

**Base URL:** `https://jurisdf.tjdft.jus.br/api/v1/pesquisa`

**Endpoints:**
- `POST /api/v1/pesquisa` - Search with filters
- `GET /api/v1/pesquisa` - Get metadata (filter values)

**Integration Method:** REST API via httpx async client

**Authentication:** None required

**Limitations:**
- Only covers acórdãos (2ª instância) - 1st instance magistrates not included
- Date filter causes 500 error (not supported)
- Max 40 results per page
- 0-indexed pagination

**Rate Limiting:** Unknown - caching recommended

### OpenAI API (Optional)

**Service Name:** OpenAI GPT

**Purpose:** AI-powered decision analysis and summarization.

**Integration Method:** OpenAI Python SDK

**Required:** `OPENAI_API_KEY` environment variable

## 6. Deployment & Infrastructure

**Deployment Options:**
- **Development:** Local with `uvicorn app.main:app --reload` or `make dev`
- **Docker:** Multi-architecture support (linux/amd64, linux/arm64)
- **Docker Swarm:** With Traefik v2 reverse proxy (recommended for production)
- **DockerHub:** `gabrielramosprof/tjdft-api:latest`

**Docker Commands:**
```bash
# Build for current platform
make build

# Build multi-arch and push
make buildx

# Development with hot reload
make dev

# Production
docker compose up -d
```

**Swarm Deployment:**
```bash
# Deploy with automatic build and push
./deploy-swarm.sh 1.0.0

# Or via Portainer UI
# Upload docker-compose.swarm.yml and deploy
```

**Cloud Provider:** Configurable (AWS, GCP, Azure, on-premise)

**Recommended Services:**
- Compute: Docker Swarm / Kubernetes / EC2 / Cloud Run
- Database: SQLite (dev), PostgreSQL (prod)
- Cache: Redis (ElastiCache / Memorystore)

**CI/CD Pipeline:** Configurable (GitHub Actions recommended)

**Monitoring & Logging:**
- Application logs: stdout/stderr (structured JSON recommended)
- Health check: `GET /health`
- Metrics: Not yet implemented

**Environment Variables:**
```bash
DATABASE_URL=          # Database connection string
REDIS_URL=             # Redis connection string
CACHE_TTL=             # Default cache TTL (seconds)
OPENAI_API_KEY=        # Optional: OpenAI API key
DEBUG=                 # Debug mode (true/false)
CORS_ORIGINS=          # Allowed CORS origins (comma-separated)
```

## 7. Security Considerations

**Authentication:** None currently implemented (open API)

**Authorization:** Not implemented

**Data Encryption:**
- TLS in transit: Configure HTTPS in production
- At rest: Configure database encryption

**Input Validation:**
- Pydantic schemas for all inputs
- Field constraints (min_length, max_length, etc.)

**CORS:** Configurable via `CORS_ORIGINS` environment variable

**Key Security Tools/Practices:**
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention via FastAPI automatic escaping
- Rate limiting: Not yet implemented (recommend adding)

## 8. Development & Testing Environment

**Local Setup Instructions:** See README.md

**Testing Frameworks:**
- pytest with pytest-asyncio
- pytest-cov for coverage
- testcontainers for integration tests (optional)

**Test Markers:**
- `unit` - Fast, isolated tests
- `integration` - Multi-layer local tests
- `api` - HTTP contract tests
- `e2e` - End-to-end tests (requires Docker)

**Code Quality Tools:**
- black (formatting, line-length 88)
- isort (import sorting)
- flake8 (linting)
- mypy (type checking)

## 9. Future Considerations / Roadmap

**Planned Features:**
- [ ] Authentication/authorization layer
- [ ] Rate limiting
- [ ] Metrics/observability (Prometheus)
- [ ] Pagination for cached decisions
- [ ] Full-text search on cached data

**Technical Debt:**
- [ ] Comprehensive error handling
- [ ] Request/response logging middleware
- [ ] Health check with database/Redis status
- [ ] OpenAPI spec customization

**Known Limitations:**
- TJDFT API doesn't support date filtering
- Only covers 2nd instance decisions (acórdãos)
- No retry queue for failed requests

## 10. Project Identification

**Project Name:** TJDFT API

**Repository URL:** https://github.com/prof-ramos/tjdft-api

**Primary Contact/Team:** Gabriel Ramos (@prof-ramos)

**Date of Last Update:** 2026-03-11

## 11. Glossary / Acronyms

| Term | Definition |
|------|------------|
| **TJDFT** | Tribunal de Justiça do Distrito Federal e Territórios |
| **Acórdão** | Judicial decision from a collegiate court (2nd instance) |
| **Relator** | The judge responsible for drafting the decision |
| **Classe CNJ** | Process class according to CNJ (Conselho Nacional de Justiça) |
| **Órgão Julgador** | The judicial body that made the decision |
| **Ementa** | Summary of the judicial decision |
| **Inteiro Teor** | Full text of the decision |
