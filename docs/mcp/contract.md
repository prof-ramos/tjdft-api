# Contrato Funcional MCP

Última atualização: 11/03/2026

## Objetivo

Este documento define o contrato funcional da camada MCP planejada para este repositório. O foco é eliminar ambiguidades antes da implementação, mantendo aderência ao comportamento já existente no código em:

- [app/schemas/consulta.py](/Users/gabrielramos/tjdft-api/app/schemas/consulta.py)
- [app/services/busca_service.py](/Users/gabrielramos/tjdft-api/app/services/busca_service.py)
- [app/services/tjdft_client.py](/Users/gabrielramos/tjdft-api/app/services/tjdft_client.py)

## Princípios do contrato

- O MCP expõe semântica externa estável e orientada a agentes.
- O contrato externo do MCP é sempre 1-indexed para paginação.
- Conversões para contratos internos 0-indexed do TJDFT acontecem apenas no adapter MCP.
- Tools core do MCP são read-only do ponto de vista do chamador.
- O MCP não documenta filtros sabidamente quebrados ou não suportados de forma confiável.

## Semântica de paginação

### Regra externa do MCP

- `page` é obrigatório apenas nas tools paginadas e começa em `1`.
- `page_size` começa em `1`.
- Valores menores que `1` são inválidos.

### Conversão interna

- Quando a tool MCP usar o cliente TJDFT, deve converter `page` para `pagina = page - 1`.
- Quando a tool MCP devolver paginação ao cliente, deve sempre reconverter para `page` 1-indexed.
- A paginação 0-indexed do TJDFT não deve vazar para o contrato MCP.

### Tamanho de página

- O limite externo recomendado do MCP é `1..40`.
- O teto `40` existe porque [tjdft_client.py](/Users/gabrielramos/tjdft-api/app/services/tjdft_client.py) força `MAX_TAMANHO = 40`.
- Se o chamador enviar valor maior que `40`, a implementação MCP deve rejeitar a entrada como inválida, em vez de depender de truncamento silencioso.

## Política de `query`

### Regra geral

- Nas tools de busca, `query` é obrigatória como campo.
- `query` pode ser string vazia (`""`).
- `query` composta apenas por espaços deve ser normalizada para `""`.

### Semântica de `query = ""`

- `query = ""` significa "sem filtro textual".
- Nesse caso, a busca retorna resultados apenas com base nos filtros estruturados informados.
- Essa decisão é compatível com o comportamento já suportado pelo cliente TJDFT em [tjdft_client.py](/Users/gabrielramos/tjdft-api/app/services/tjdft_client.py).

### Quando rejeitar

- `query = null` é inválida.
- Tipos diferentes de string são inválidos.

## Filtros oficialmente suportados no MCP

Os filtros abaixo são os únicos que entram no contrato oficial inicial do MCP.

| Filtro MCP | Tipo | Encaminhamento interno | Status |
| --- | --- | --- | --- |
| `relator` | `string` | `relator` -> `nomeRelator` | suportado |
| `classe` | `string` | `classe` -> `descricaoClasseCnj` | suportado |
| `orgao_julgador` | `string` | `orgao_julgador` -> `descricaoOrgaoJulgador` | suportado |
| `base` | `string` | `base` -> `base` | suportado |
| `subbase` | `string` | `subbase` -> `subbase` | suportado |
| `processo` | `string` | `processo` -> `processo` | suportado |
| `revisor` | `string` | `revisor` -> `nomeRevisor` | suportado |
| `relator_designado` | `string` | `relator_designado` -> `nomeRelatorDesignado` | suportado |

### Filtros explicitamente fora do contrato

Os filtros abaixo não fazem parte do contrato MCP inicial:

| Filtro | Motivo |
| --- | --- |
| `data_inicio` | [busca_service.py](/Users/gabrielramos/tjdft-api/app/services/busca_service.py) ainda encaminha, mas [tjdft_client.py](/Users/gabrielramos/tjdft-api/app/services/tjdft_client.py) documenta filtro por data como não suportado e sujeito a erro 500 no upstream |
| `data_fim` | Mesmo motivo de `data_inicio` |
| Qualquer chave fora da lista oficial | Não há suporte contratual no MCP |

### Política de validação de filtros

- `relator`, `classe` e `orgao_julgador` devem ser tratados como filtros com validação de domínio, pois já existe validação no projeto via `app.utils.filtros`.
- `base`, `subbase`, `processo`, `revisor` e `relator_designado` são filtros passthrough: o MCP aceita strings e delega ao cliente TJDFT sem validação local forte.
- Chaves desconhecidas em `filters` devem gerar erro de entrada inválida.

## Resultado vazio versus erro

### Busca sem resultados

Busca sem resultados não é erro.

O retorno deve ser sucesso, com envelope vazio:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

### Regras

- `items = []` representa resultado vazio legítimo.
- `total = 0` deve acompanhar busca vazia.
- A tool não deve lançar exceção apenas porque nenhuma decisão foi encontrada.

## Política de erros

### Categorias mínimas

O MCP deve mapear falhas para categorias acionáveis e estáveis:

| Categoria | Quando usar |
| --- | --- |
| `invalid_params` | `page < 1`, `page_size` fora da faixa, tipo inválido, filtro desconhecido, valor inválido para filtros validados |
| `not_found` | recurso individual inexistente, como `consulta_id` ausente ou decisão não localizada no cache local |
| `upstream_error` | erro retornado pelo TJDFT |
| `timeout` | timeout de rede na chamada upstream |
| `internal_error` | falha inesperada no adapter MCP |

### Regras de mapeamento

- Falha de validação local nunca deve virar `internal_error`.
- Resultado vazio nunca deve virar `not_found` nas tools de busca.
- `not_found` é reservado para lookup de recurso identificado por chave única.

## Política de side effects

### Regra obrigatória

As tools core do MCP devem ser read-only e publicadas com `readOnlyHint=true`.

### Consequência arquitetural

Para cumprir essa regra, a camada MCP não deve chamar fluxos que persistem histórico ou escrevem cache relacional como efeito colateral da busca.

Em particular:

- não deve usar diretamente [BuscaService.buscar()](/Users/gabrielramos/tjdft-api/app/services/busca_service.py) como implementação da busca MCP, porque esse fluxo grava `Consulta` e faz cache de decisões;
- não deve usar diretamente [BuscaService.buscar_todas_paginas()](/Users/gabrielramos/tjdft-api/app/services/busca_service.py) como implementação da busca agregada MCP, pelo mesmo motivo.

### O que é permitido

- leitura da API TJDFT;
- leitura de metadados de referência;
- leitura de histórico já existente;
- leitura de decisões previamente cacheadas;
- uso de cache apenas em memória/processo se não introduzir persistência observável como side effect contratual.

### O que é proibido nas tools core

- criar `Consulta`;
- persistir `Decisao` como efeito colateral da busca;
- alterar estado de banco para atender uma chamada MCP de leitura.

## Consistência com o código atual

Checklist consolidado:

- paginação externa 1-indexed já é o padrão público em [consulta.py](/Users/gabrielramos/tjdft-api/app/schemas/consulta.py);
- cliente TJDFT continua 0-indexed em [tjdft_client.py](/Users/gabrielramos/tjdft-api/app/services/tjdft_client.py);
- `query` vazia já é suportada pelo cliente TJDFT;
- `data_inicio` e `data_fim` não entram no contrato MCP por serem inseguros no upstream;
- `BuscaService` atual possui side effects e, por isso, não deve ser a implementação direta das tools core read-only.
