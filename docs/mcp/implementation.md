# MCP Implementation Guide

Última atualização: 11/03/2026

## Overview

A camada MCP (Model Context Protocol) deste projeto expõe busca de jurisprudência do TJDFT como ferramentas para agentes de IA. O servidor é implementado usando FastMCP e roda via `stdio`.

## Directory Structure

```
app/mcp/
├── __init__.py           # Package init
├── __main__.py           # Entry point executável (python -m app.mcp)
├── server.py             # FastMCP server + lifespan
├── runtime.py            # MCPRuntime (cache, DB sessions, TJDFT client, AI service)
├── constants.py          # Enums (ResponseFormat, etc.)
├── errors.py             # Error mapping to MCP error types
├── formatters.py         # Response formatting (markdown/JSON)
├── schemas.py            # Pydantic input schemas para tools
└── tools/
    ├── __init__.py       # Registry export
    ├── search_tools.py   # tjdft_search_decisions, tjdft_get_metadata, tjdft_search_all_pages
    ├── history_tools.py  # tjdft_get_consulta, tjdft_list_history, tjdft_find_similar_decisions
    └── ai_tools.py       # tjdft_ai_summarize, tjdft_ai_extract_theses, tjdft_ai_compare_decisions
```

## Runtime Lifecycle

O `MCPRuntime` gerencia recursos compartilhados com lifecycle explícito:

1. **Startup** (`app_lifespan` em `server.py`):
   - `runtime.initialize()` cria CacheManager e AIService (opcional)
   - Registra tools nos 3 módulos: search, history, AI

2. **Request handling**:
   - Cada tool recebe `params` validados (Pydantic schemas)
   - Usa context managers do runtime: `runtime.session()`, `runtime.tjdft_client()`, `runtime.optional_ai_service()`
   - Formata resposta via `format_response()` com markdown/JSON

3. **Shutdown**:
   - `runtime.close()` encerra AIService (se inicializado) e CacheManager
   - Sessões DB são fechadas automaticamente pelos context managers

## Available Tools

### Search Tools (TJDFT API)
- `tjdft_search_decisions` - Busca paginada com filtros (1-indexed)
- `tjdft_get_metadata` - Retorna listas de referência para filtros
- `tjdft_search_all_pages` - Agrega múltiplas páginas sem persistir

### History Tools (Local DB)
- `tjdft_get_consulta` - Recupera consulta persistida por ID
- `tjdft_list_history` - Lista histórico de consultas
- `tjdft_find_similar_decisions` - Busca similares no cache local

### AI Tools (Opcional, requer OPENAI_API_KEY)
- `tjdft_ai_summarize` - Resumo analítico de ementa
- `tjdft_ai_extract_theses` - Extrai teses jurídicas
- `tjdft_ai_compare_decisions` - Compara múltiplas decisões

## Usage Examples

### Claude Desktop Configuration

Adicione ao seu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tjdft-api": {
      "command": "uv",
      "args": ["run", "python", "-m", "app.mcp"],
      "cwd": "/Users/gabrielramos/tjdft-api",
      "env": {
        "DATABASE_URL": "sqlite+aiosqlite:///./tjdft.db",
        "MCP_ENABLE_AI_TOOLS": "true"
      }
    }
  }
}
```

### Command-line Testing

```bash
# Executar servidor
uv run python -m app.mcp

# O servidor fica aguardando chamadas MCP via stdin/stdout
```

## Response Format

Todas as tools suportam `response_format`:

- `markdown` (padrão): Formato legível para humanos
- `json`: Estrutura estrita para parsing automatizado

## Configuration

Variáveis de ambiente relevantes para MCP:

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `MCP_CHARACTER_LIMIT` | `25000` | Limite de caracteres por resposta |
| `MCP_ENABLE_AI_TOOLS` | `false` | Habilita tools de IA |
| `MCP_REQUEST_TIMEOUT_SECONDS` | `30.0` | Timeout upstream |
| `OPENAI_API_KEY` | - | Necessário para tools de IA |

Veja [`configuration.md`](/Users/gabrielramos/tjdft-api/docs/mcp/configuration.md) para detalhes completos.

## Contract Details

Para especificações funcionais completas (paginação, filtros, políticas de erro), consulte [`contract.md`](/Users/gabrielramos/tjdft-api/docs/mcp/contract.md).

Para catálogo completo de tools com exemplos de input/output, consulte [`tool_catalog.md`](/Users/gabrielramos/tjdft-api/docs/mcp/tool_catalog.md).

## Troubleshooting

### Servidor não inicia
- Verifique se `.venv` existe e dependências instaladas: `uv pip install -e ".[dev]"`
- Confirme que `DATABASE_URL` está configurada

### Tools de IA não aparecem
- Verifique `MCP_ENABLE_AI_TOOLS=true`
- Confirme `OPENAI_API_KEY` definida

### Erro "database is locked" (SQLite)
- O SQLite configuration automático em `app/core/sqlite_config.py` deve resolver
- Se persistir, aumente `busy_timeout` na configuração

### Timeout no TJDFT
- Aumente `MCP_REQUEST_TIMEOUT_SECONDS` (padrão: 30s)
- Verifique conectividade com `jurisdf.tjdft.jus.br`

## Development

### Adicionar nova tool

1. Criar schema em `app/mcp/schemas.py`
2. Implementar função `run_*()` em módulo `tools/*_tools.py`
3. Registrar com `@mcp.tool()` e decorar com `ToolAnnotations`
4. Adicionar documentação em `tool_catalog.md`

### Testar localmente

Use o cliente MCP inspect ou Claude Desktop com configuração apontando para o diretório do projeto.
