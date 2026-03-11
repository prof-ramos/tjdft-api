# Quickstart MCP (TJDFT)

Este guia mostra como executar o servidor MCP do projeto via `stdio`.

## Pré-requisitos

- `uv` instalado
- ambiente virtual `.venv` criado
- dependências instaladas

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Executar o servidor MCP

```bash
uv run python -m app.mcp
```

Observação: o processo fica em execução aguardando chamadas MCP por `stdin/stdout`.

## Tools core disponíveis

- `tjdft_search_decisions`
- `tjdft_get_metadata`
- `tjdft_search_all_pages`
- `tjdft_get_consulta`
- `tjdft_list_history`
- `tjdft_find_similar_decisions`

## Exemplo de configuração de cliente MCP

Veja o arquivo [example.mcp.json](/Users/gabrielramos/tjdft-api/docs/mcp/example.mcp.json).
