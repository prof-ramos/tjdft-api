# Catálogo de Tools MCP

Última atualização: 11/03/2026

## Escopo

Este catálogo descreve as tools core previstas para o MCP do projeto, com foco em contrato, filtros suportados e comportamento observável. Todas as definições abaixo seguem [contract.md](/Users/gabrielramos/tjdft-api/docs/mcp/contract.md).

## Regras globais

- Todas as tools core devem ser read-only.
- Todas as tools core devem ser publicadas com `readOnlyHint=true`.
- Paginação externa usa `page` 1-indexed.
- `page_size` deve ficar entre `1` e `40`.
- Busca sem resultado retorna sucesso com lista vazia.
- Chaves de filtro fora da lista oficial devem gerar `invalid_params`.

## Matriz oficial de filtros

| Filtro | Tools que aceitam | Validação local |
| --- | --- | --- |
| `relator` | `tjdft_search_decisions`, `tjdft_search_all_pages` | sim |
| `classe` | `tjdft_search_decisions`, `tjdft_search_all_pages` | sim |
| `orgao_julgador` | `tjdft_search_decisions`, `tjdft_search_all_pages` | sim |
| `base` | `tjdft_search_decisions`, `tjdft_search_all_pages` | não |
| `subbase` | `tjdft_search_decisions`, `tjdft_search_all_pages` | não |
| `processo` | `tjdft_search_decisions`, `tjdft_search_all_pages` | não |
| `revisor` | `tjdft_search_decisions`, `tjdft_search_all_pages` | não |
| `relator_designado` | `tjdft_search_decisions`, `tjdft_search_all_pages` | não |

## `tjdft_search_decisions`

### Finalidade

Busca paginada de decisões no TJDFT, com contrato externo estável para agentes.

### Entrada

```json
{
  "query": "tributário",
  "filters": {
    "classe": "APC",
    "orgao_julgador": "6CC"
  },
  "page": 1,
  "page_size": 20
}
```

### Regras

- `query` aceita `""`.
- `filters` é opcional.
- `page` é 1-indexed.
- A implementação converte internamente para `pagina = page - 1`.

### Saída mínima

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

### Comportamento de erro

- filtros desconhecidos: `invalid_params`
- filtros validados com valor inválido: `invalid_params`
- falha de rede/upstream: `upstream_error` ou `timeout`

## `tjdft_get_metadata`

### Finalidade

Retorna metadados de apoio à busca, como listas de referência para montagem de filtros válidos.

### Entrada

Sem parâmetros obrigatórios.

### Saída esperada

Estrutura contendo ao menos os conjuntos de referência já usados pelo projeto:

- relatores
- classes
- órgãos julgadores
- assuntos, quando disponíveis na fonte de referência local

### Regras

- Não executa busca textual.
- Não persiste nada.

## `tjdft_search_all_pages`

### Finalidade

Executa coleta agregada de múltiplas páginas de busca, preservando o contrato read-only.

### Entrada

```json
{
  "query": "",
  "filters": {
    "relator": "desembargador-faustolo"
  },
  "max_pages": 3,
  "page_size": 40
}
```

### Regras

- `query = ""` é permitido.
- `max_pages` deve ser inteiro maior ou igual a `1`.
- `page_size` segue o teto de `40`.
- A tool agrega os resultados sem criar histórico de consulta.

### Saída mínima

```json
{
  "items": [],
  "total": 0,
  "pages_fetched": 0,
  "page_size": 40
}
```

### Observação de contrato

Esta tool não deve reutilizar diretamente o fluxo atual de [BuscaService.buscar_todas_paginas()](/Users/gabrielramos/tjdft-api/app/services/busca_service.py), porque esse fluxo hoje persiste dados.

## `tjdft_get_consulta`

### Finalidade

Ler uma consulta já existente no histórico local por `consulta_id`.

### Entrada

```json
{
  "consulta_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Regras

- UUID malformado: `invalid_params`
- consulta inexistente: `not_found`
- leitura apenas; sem atualização de timestamp ou qualquer escrita derivada

## `tjdft_list_history`

### Finalidade

Listar histórico já persistido de consultas.

### Entrada

```json
{
  "usuario_id": "123e4567-e89b-12d3-a456-426614174000",
  "limit": 20
}
```

### Regras

- `usuario_id` é opcional.
- `limit` deve ser inteiro maior ou igual a `1`.
- se não houver histórico, retorna `items: []`.

## `tjdft_find_similar_decisions`

### Finalidade

Encontrar decisões similares a partir de uma decisão já disponível no cache relacional/local do projeto.

### Entrada

```json
{
  "uuid_tjdft": "uuid-da-decisao",
  "limit": 10
}
```

### Regras

- depende apenas de leitura do cache local existente;
- não deve disparar nova persistência para enriquecer o cache;
- decisão de referência ausente no cache: `not_found`;
- sem similares: retorna `items: []`.

## Política de resultados vazios

| Tool | Resultado vazio |
| --- | --- |
| `tjdft_search_decisions` | sucesso com `items: []` |
| `tjdft_search_all_pages` | sucesso com `items: []` |
| `tjdft_list_history` | sucesso com `items: []` |
| `tjdft_find_similar_decisions` | sucesso com `items: []` |
| `tjdft_get_consulta` | `not_found` |

## Política de side effects por tool

| Tool | Side effects permitidos |
| --- | --- |
| `tjdft_search_decisions` | nenhum persistente |
| `tjdft_get_metadata` | nenhum |
| `tjdft_search_all_pages` | nenhum persistente |
| `tjdft_get_consulta` | nenhum |
| `tjdft_list_history` | nenhum |
| `tjdft_find_similar_decisions` | nenhum |

## Decisões de implementação derivadas deste catálogo

- adapters MCP de busca devem preferir `TJDFTClient` ou wrappers read-only dedicados;
- `BuscaService` pode continuar existindo para a API HTTP do projeto, mas não define sozinho o contrato do MCP;
- qualquer ampliação futura de filtros deve atualizar este catálogo antes de entrar no contrato público MCP.
