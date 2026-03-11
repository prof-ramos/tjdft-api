# API de Jurisprudência do TJDFT — Documentação Completa

**Base URL:** `https://jurisdf.tjdft.jus.br/api/v1`

---

## Endpoints

### 1. `GET /pesquisa` — Metadados

Retorna as listas de valores válidos para uso nos filtros. **Não faz busca.**

```http
GET https://jurisdf.tjdft.jus.br/api/v1/pesquisa
```

**Resposta:**
```json
{
  "relatores": ["ADELITH CASTRO DE CARVALHO LOPES", "..."],  // 228 nomes
  "revisores": ["ALFEU MACHADO", "..."],                      // 63 nomes
  "designados": ["ADELITH CASTRO DE CARVALHO LOPES", "..."], // 200 nomes
  "classes": ["AGRAVO", "APELAÇÃO CÍVEL", "..."],            // 125 classes
  "orgaos": [                                                 // 33 grupos
    {
      "base": "CONSELHO ESPECIAL",
      "agregador": false,
      "items": ["CONSELHO ESPECIAL"]
    }
  ]
}
```

**Uso:** Consultar antes de usar filtros para garantir que os valores existem.

---

### 2. `POST /pesquisa` — Busca de Acórdãos

Endpoint principal de busca. Retorna acórdãos paginados com agregações.

```http
POST https://jurisdf.tjdft.jus.br/api/v1/pesquisa
Content-Type: application/json
```

#### Body (todos os campos)

```json
{
  "query": "responsabilidade civil",
  "pagina": 0,
  "tamanho": 20,
  "termosAcessorios": [
    {"campo": "nomeRelator",            "valor": "CARMEN BITTENCOURT"},
    {"campo": "descricaoClasseCnj",     "valor": "APELAÇÃO CÍVEL"},
    {"campo": "descricaoOrgaoJulgador", "valor": "1ª TURMA CÍVEL"},
    {"campo": "base",                   "valor": "acordaos"},
    {"campo": "relatorDesignado",       "valor": "GEORGE LOPES"},
    {"campo": "revisor",                "valor": "ANA CANTARINO"},
    {"campo": "segredoJustica",         "valor": "0"}
  ]
}
```

| Campo | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `query` | string | **sim** | — | Texto de busca. Pode ser `""` para busca ampla |
| `pagina` | int | não | `0` | Página (0-indexed) |
| `tamanho` | int | não | `20` | Resultados por página. **Mín: 1, Máx: 40** |
| `termosAcessorios` | array | não | `[]` | Filtros `[{campo, valor}]` |

#### Campos válidos em `termosAcessorios`

| `campo` | Descrição | Fonte dos valores |
|---|---|---|
| `nomeRelator` | Nome exato do relator | GET /pesquisa → `relatores` |
| `nomeRevisor` | Nome exato do revisor | GET /pesquisa → `revisores` |
| `nomeRelatorDesignado` | Nome do relator designado | GET /pesquisa → `designados` |
| `descricaoClasseCnj` | Classe processual | GET /pesquisa → `classes` |
| `descricaoOrgaoJulgador` | Órgão julgador | GET /pesquisa → `orgaos[].items[]` |
| `base` | Base documental: `acordaos` ou `decisoes` | Fixo |
| `subbase` | Subbase: `acordaos`, `acordaos-tr`, `decisoes-monocraticas` | Fixo |
| `processo` | Número CNJ do processo | Livre |
| `uuid` | UUID da decisão | Livre |
| `identificador` | ID numérico da decisão | Livre |
| `origem` | Origem da decisão | Livre |

> **Atenção:** Os campos `revisor`, `relatorDesignado` e `segredoJustica` são **rejeitados** pela API com erro 400. Use `nomeRevisor` e `nomeRelatorDesignado`.

#### Resposta

```json
{
  "hits": {"value": 720461},
  "paginacao": {"pagina": 0, "tamanho": 20},
  "agregacoes": {
    "relator":          [{"nome": "ALFEU MACHADO", "total": 15872}],
    "relatorDesignado": [{"nome": "ADELITH...", "total": 34}],
    "revisor":          [{"nome": "ALFEU MACHADO", "total": 965}],
    "orgaoJulgador":    [{"nome": "1ª TURMA CÍVEL", "total": 67735}],
    "base": [
      {"nome": "acordaos", "total": 517680,
       "filhos": [
         {"nome": "acordaos",    "total": 444579},
         {"nome": "acordaos-tr", "total": 73101}
       ]}
    ],
    "segredoJustica": [{"nome": 0, "total": 509693}],
    "classe":         [{"nome": "APELAÇÃO CÍVEL", "total": 112000}]
  },
  "registros": [ /* ver estrutura do registro abaixo */ ]
}
```

#### Estrutura de um Registro

| Campo | Tipo | Descrição |
|---|---|---|
| `sequencial` | int | Posição na página (1-based) |
| `base` | string | `"acordaos"` ou `"acordaos-tr"` |
| `uuid` | string | Identificador UUID único |
| `identificador` | string | ID numérico do acórdão |
| `dataJulgamento` | string | Data ISO 8601: `"2025-03-04T03:00:00.000Z"` |
| `dataPublicacao` | string | Data ISO 8601 de publicação |
| `decisao` | string | Dispositivo da decisão |
| `ementa` | string | Ementa completa |
| `processo` | string | Número CNJ: `"0701880-23.2024.8.07.0018"` |
| `nomeRelator` | string | Nome do relator |
| `relatorAtivo` | bool | Se relator ainda está ativo no tribunal |
| `descricaoOrgaoJulgador` | string | Órgão julgador |
| `turmaRecursal` | bool | Se é decisão de turma recursal |
| `segredoJustica` | bool | Se está em segredo de justiça |
| `inteiroTeorHtml` | string | Texto completo em HTML (pode estar indisponível) |
| `possuiInteiroTeor` | bool | Se inteiro teor está disponível |
| `marcadores` | dict | Trechos destacados da busca |
| `localDePublicacao` | string | `"PJe"`, `"DJDFT"`, etc. |
| `uf` | string | Sempre `"DF"` |

---

## Cobertura dos Dados

| Subbase | Descrição | Total aprox. |
|---|---|---|
| `acordaos` | Acórdãos do TJDFT (câmaras, turmas, conselhos) | ~444.579 |
| `acordaos-tr` | Acórdãos de Turmas Recursais (Juizados Especiais) | ~73.101 |
| `decisoes-monocraticas` | Decisões monocráticas (1ª e 2ª instância) | ~13.831+ |
| **Total** | | **~531.000+** |

> Decisões monocráticas têm estrutura diferente dos acórdãos: não possuem `dataJulgamento`, `decisao`, `localDePublicacao`, `relatorAtivo`, `turmaRecursal` — mas incluem `inteiroTeor` (string) e `jurisprudenciaEmFoco`.

---

## Limitações Conhecidas

| # | Limitação | Impacto |
|---|---|---|
| 1 | **Filtro por data causa erro 500** — `dataJulgamento`/`dataPublicacao` via `termosAcessorios` é rejeitado pelo servidor | Não é possível filtrar por período |
| 2 | **Sem ordenação** — campos `ordenacao`, `direcao`, `sort` são rejeitados (400) | Resultados seguem ordem interna da API |
| 3 | **Máximo 40 por página** — `tamanho > 40` retorna erro 400 | Paginação obrigatória para grandes volumes |
| 4 | **Paginação 0-indexed** — primeira página é `pagina: 0` | Atenção ao implementar paginação |
| 5 | **`nomeRelator` deve ser exato** — sem busca parcial no filtro | Verificar contra a lista de 228 nomes antes de filtrar |
| 6 | **Magistrados de 1ª instância** — não aparecem na lista de relatores do GET /pesquisa | Buscar pelo nome via `query` ou `processo` |
| 7 | **`query` vazio (`""`) é válido** — retorna todos os registros com filtros aplicados | Útil para listar decisões de relator sem tema |
| 8 | **Decisões monocráticas têm estrutura diferente** — sem `dataJulgamento`, `decisao`, `localDePublicacao` | Tratar `subbase` para adaptar parsing |

---

## Exemplos Práticos

### Buscar decisões recentes de um relator

```python
import httpx

url = "https://jurisdf.tjdft.jus.br/api/v1/pesquisa"

payload = {
    "query": "",
    "termosAcessorios": [{"campo": "nomeRelator", "valor": "CARMEN BITTENCOURT"}],
    "pagina": 0,
    "tamanho": 20
}

response = httpx.post(url, json=payload)
data = response.json()
print(f"Total: {data['hits']['value']} acórdãos")
for r in data['registros']:
    print(r['dataJulgamento'], r['processo'], r['decisao'][:80])
```

### Buscar por tema em turma específica

```python
payload = {
    "query": "dano moral consumidor",
    "termosAcessorios": [
        {"campo": "descricaoOrgaoJulgador", "valor": "3ª TURMA CÍVEL"},
        {"campo": "descricaoClasseCnj",     "valor": "APELAÇÃO CÍVEL"}
    ],
    "pagina": 0,
    "tamanho": 40
}
```

### Autocomplete de relator (nome parcial)

```python
# 1. Buscar lista de relatores
meta = httpx.get(url).json()
relatores = meta['relatores']

# 2. Filtrar por nome parcial
nome_parcial = "TEIXEIRA"
matches = [r for r in relatores if nome_parcial.upper() in r]
# -> ['JOÃO BATISTA TEIXEIRA', 'ROBSON TEIXEIRA DE FREITAS']

# 3. Usar o match exato no filtro
payload = {
    "query": "",
    "termosAcessorios": [{"campo": "nomeRelator", "valor": matches[0]}],
    "pagina": 0,
    "tamanho": 20
}
```

### Paginação completa

```python
async def buscar_todas_paginas(query: str, filtros: list, max_paginas: int = 10):
    resultados = []
    pagina = 0

    while pagina < max_paginas:
        payload = {
            "query": query,
            "termosAcessorios": filtros,
            "pagina": pagina,
            "tamanho": 40  # máximo
        }
        r = httpx.post(url, json=payload)
        data = r.json()
        registros = data.get('registros', [])

        if not registros:
            break

        resultados.extend(registros)

        total = data['hits']['value']
        if len(resultados) >= total:
            break

        pagina += 1

    return resultados
```

---

## Comportamento do Campo `agregacoes`

As agregações retornam **sempre** os top valores para cada dimensão, baseados na query atual. Use-as para:

1. **Descobrir relatores** que têm decisões sobre um tema
2. **Ver distribuição** por órgão/classe
3. **Validar filtros** antes de aplicar

```python
payload = {"query": "improbidade administrativa", "pagina": 0, "tamanho": 1}
data = httpx.post(url, json=payload).json()

# Relatores com mais acórdãos sobre o tema
for item in data['agregacoes']['relator'][:5]:
    print(f"{item['nome']}: {item['total']} acórdãos")
```

---

## Dicionário de Valores Válidos

O arquivo `docs/tjdft_api_dictionary.json` contém:

- Lista completa de **228 relatores**
- Lista completa de **63 revisores**
- Lista completa de **200 relatores designados**
- Lista completa de **125 classes processuais**
- Lista completa de **33 grupos de órgãos** com variantes de nome
- Contagem de acórdãos por relator
- Exemplos de payloads para cada estratégia de busca
- Lista de campos não suportados

Consulte sempre `tjdft_api_dictionary.json` antes de montar filtros para garantir valores exatos.

---

## Notas para Agentes de IA

1. **Antes de filtrar por relator:** verificar se o nome existe em `relatores[]` do dicionário usando busca por substring (ex: "TEIXEIRA" → listar matches → usar exato)
2. **Nome não encontrado:** provavelmente é juiz de 1ª instância — informar ao usuário que a API cobre apenas acórdãos
3. **`query` pode ser vazio** quando o objetivo é listar por relator/órgão sem tema específico
4. **Agregações são aliadas:** fazer busca com `tamanho: 1` primeiro para ver quais relatores têm acórdãos sobre o tema antes de filtrar
5. **Paginação começa em 0**, não em 1
6. **Sem suporte a datas:** não é possível filtrar por período via API — ordenação cronológica não é garantida
