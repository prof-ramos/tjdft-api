# APIs Públicas do TJDFT — Documentação Completa

**Fonte:** https://www.tjdft.jus.br/transparencia/tecnologia-da-informacao-e-comunicacao/dados-abertos/webservice-ou-api
**Última atualização da fonte:** 27/03/2025
**Autenticação:** Nenhuma — todas as APIs são públicas
**Formato:** JSON

---

## API 1: Jurisprudência

### `GET /api/v1/pesquisa` — Metadados

```
GET https://jurisdf.tjdft.jus.br/api/v1/pesquisa
```

Retorna listas de valores válidos para uso nos filtros. **Não busca decisões.**

**Resposta:**
```json
{
  "relatores":  ["NOME DO RELATOR", "..."],   // 228 nomes
  "revisores":  ["NOME DO REVISOR", "..."],    // 63 nomes
  "designados": ["NOME DO DESIGNADO", "..."],  // 200 nomes
  "classes":    ["APELAÇÃO CÍVEL", "..."],     // 125 classes
  "orgaos": [
    {"base": "1ª TURMA CÍVEL", "agregador": false, "items": ["1ª TURMA CÍVEL", "1ª Turma Civel"]}
  ]  // 33 grupos com variantes de nome
}
```

---

### `POST /api/v1/pesquisa` — Pesquisa de Decisões

```
POST https://jurisdf.tjdft.jus.br/api/v1/pesquisa
Content-Type: application/json
```

Cobre **acórdãos** e **decisões monocráticas** (~531 mil documentos).

#### Body

| Campo | Tipo | Obrig. | Desc. |
|---|---|---|---|
| `query` | string | **sim** | Texto livre. `""` é válido (retorna tudo com filtros aplicados) |
| `pagina` | int | **sim** | Página **0-indexed** (primeira = 0) |
| `tamanho` | int | **sim** | Resultados por página. **Mín: 1, Máx: 40** |
| `termosAcessorios` | array | não | Filtros adicionais: `[{"campo": "...", "valor": "..."}]` |

#### Campos válidos em `termosAcessorios`

| `campo` | Descrição | Valores |
|---|---|---|
| `nomeRelator` | Nome exato do relator | Lista do GET /pesquisa → relatores |
| `nomeRevisor` | Nome exato do revisor | Lista do GET /pesquisa → revisores |
| `nomeRelatorDesignado` | Relator designado | Lista do GET /pesquisa → designados |
| `descricaoClasseCnj` | Classe processual | Lista do GET /pesquisa → classes |
| `descricaoOrgaoJulgador` | Órgão julgador | Lista do GET /pesquisa → orgaos[].items[] |
| `base` | Base documental | `"acordaos"` ou `"decisoes"` |
| `subbase` | Subbase | `"acordaos"`, `"acordaos-tr"`, `"decisoes-monocraticas"` |
| `processo` | Número CNJ | Ex: `"0702180-36.2024.8.07.0001"` |
| `uuid` | UUID da decisão | UUID string |
| `identificador` | ID numérico | String numérica |
| `identificadorOrdenacao` | ID para ordenação | String |
| `origem` | Origem da decisão | String |
| `dataJulgamento` | ⚠️ Data julgamento | `YYYY-MM-DD` — **causa erro 500, não usar** |
| `dataPublicacao` | ⚠️ Data publicação | `YYYY-MM-DD` — **causa erro 500, não usar** |

> **Campos rejeitados (400):** `revisor`, `relatorDesignado`, `segredoJustica`, `q`, `ordenacao`, `direcao`

#### Resposta

```json
{
  "hits": {"value": 531000},
  "paginacao": {"pagina": 0, "tamanho": 20},
  "agregacoes": {
    "relator":          [{"nome": "CARMEN BITTENCOURT", "total": 6072}],
    "relatorDesignado": [{"nome": "...", "total": 0}],
    "revisor":          [{"nome": "...", "total": 0}],
    "orgaoJulgador":    [{"nome": "1ª TURMA CÍVEL", "total": 67735}],
    "base":             [{"nome": "acordaos", "total": 517680, "filhos": [...]}],
    "segredoJustica":   [{"nome": 0, "total": 509693}],
    "classe":           [{"nome": "APELAÇÃO CÍVEL", "total": 106932}]
  },
  "registros": [...]
}
```

#### Estrutura de um Registro (Acórdão)

| Campo | Tipo | Desc. |
|---|---|---|
| `sequencial` | int | Posição na página |
| `base` | str | `"acordaos"` |
| `subbase` | str | `"acordaos"` ou `"acordaos-tr"` |
| `uuid` | str | UUID único |
| `identificador` | str | ID numérico |
| `dataJulgamento` | str | ISO 8601 |
| `dataPublicacao` | str | ISO 8601 |
| `decisao` | str | Dispositivo da decisão |
| `ementa` | str | Ementa completa |
| `localDePublicacao` | str | `"PJe"`, `"DJDFT"` etc. |
| `processo` | str | Número CNJ |
| `nomeRelator` | str | Nome do relator |
| `relatorAtivo` | bool | Se relator está ativo |
| `uf` | str | Sempre `"DF"` |
| `segredoJustica` | bool | |
| `turmaRecursal` | bool | |
| `descricaoOrgaoJulgador` | str | Órgão julgador |
| `versao` | str | |
| `codigoClasseCnj` | int | Código CNJ da classe |
| `codigoSistjOrgaoJulgador` | int | Código interno do órgão |
| `inteiroTeorHtml` | str | Texto integral em HTML |
| `possuiInteiroTeor` | bool | |
| `marcadores` | dict | Trechos destacados |

#### Diferenças nas Decisões Monocráticas (`subbase=decisoes-monocraticas`)

Campos **ausentes**: `dataJulgamento`, `decisao`, `localDePublicacao`, `relatorAtivo`, `uf`, `segredoJustica`, `turmaRecursal`, `inteiroTeorHtml`
Campos **presentes só aqui**: `inteiroTeor` (string), `jurisprudenciaEmFoco` (array), `descricaoOrgao`

---

#### Exemplos de Uso

**Buscar por relator:**
```json
{"query": "", "termosAcessorios": [{"campo": "nomeRelator", "valor": "CARMEN BITTENCOURT"}], "pagina": 0, "tamanho": 20}
```

**Buscar por processo:**
```json
{"query": "", "termosAcessorios": [{"campo": "processo", "valor": "0702180-36.2024.8.07.0001"}], "pagina": 0, "tamanho": 10}
```

**Filtros combinados:**
```json
{"query": "dano moral", "termosAcessorios": [{"campo": "nomeRelator", "valor": "ANA CANTARINO"}, {"campo": "descricaoClasseCnj", "valor": "APELAÇÃO CÍVEL"}], "pagina": 0, "tamanho": 40}
```

**Decisões monocráticas:**
```json
{"query": "tutela antecipada", "termosAcessorios": [{"campo": "subbase", "valor": "decisoes-monocraticas"}], "pagina": 0, "tamanho": 20}
```

---

## API 2: Recursos Humanos

**Base URL:** `https://rest-rh.tjdft.jus.br/api/transparencia/`
**Contato:** SEGP (61) 3103-6698 | NUGCOM (61) 3103-4290
**Atualização:** Automática | **Método:** GET | **Auth:** Nenhuma

---

### `GET /teletrabalho` — Servidores em Teletrabalho

```
GET https://rest-rh.tjdft.jus.br/api/transparencia/teletrabalho
```

Situação atual dos servidores em regime de teletrabalho.

**Resposta:**
```json
[{"Nome": "Abigail Junqueira Torres"}, {"Nome": "Abner Silveira dos Santos"}]
```

---

### `GET /estagiarios` — Estagiários

```
GET https://rest-rh.tjdft.jus.br/api/transparencia/estagiarios
```

Situação atual dos estagiários vinculados ao TJDFT.

**Resposta:**
```json
[{"Nome": "Ábner Miguel Godois"}, {"Nome": "Adryelle Silva Santos"}]
```

---

### `GET /cedidos/1/:mes/:ano` — Cedidos TJDFT → Outros Órgãos

```
GET https://rest-rh.tjdft.jus.br/api/transparencia/cedidos/1/{mes}/{ano}
```

**Parâmetros:** `mes` (1-12), `ano` (ex: 2025)
**Exemplo:** `GET .../cedidos/1/3/2025`

| Campo | Descrição |
|---|---|
| `Matr` | Matrícula |
| `Nome` | Nome |
| `DtInicioCessao` | Data início da cessão (YYYY-MM-DD) |
| `DtRetornoCessao` | Data encerramento (YYYY-MM-DD ou null) |
| `FCCJ` | Função Comissionada/Cargo em Comissão |
| `Sigla` | Sigla do órgão de destino |
| `RazaoSocial` | Nome do órgão de destino |

---

### `GET /cedidos/2/:mes/:ano` — Cedidos Outros Órgãos → TJDFT

```
GET https://rest-rh.tjdft.jus.br/api/transparencia/cedidos/2/{mes}/{ano}
```

Mesmos campos da API anterior. `Sigla`/`RazaoSocial` referem-se ao **órgão de origem**.

---

### `GET /cedidos/3/:mes/:ano` — Anistiados de Outros Órgãos no TJDFT

```
GET https://rest-rh.tjdft.jus.br/api/transparencia/cedidos/3/{mes}/{ano}
```

Mesmos campos. Servidores anistiados políticos de outros órgãos em exercício no TJDFT.

---

### `GET /servidoresNaoIntegrantes` — Servidores Não Integrantes do Quadro

```
GET https://rest-rh.tjdft.jus.br/api/transparencia/servidoresNaoIntegrantes
```

Servidores em exercício no TJDFT sem vínculo efetivo (requisitados, cedidos, temporários).

| Campo | Descrição |
|---|---|
| `Nome` | Nome |
| `CargoOrgaoOrigem` | Cargo no órgão de origem |
| `RazaoSocial` | Nome do órgão de origem |
| `Poder` | Poder do Estado (ex: Executivo, Judiciário) |
| `Regime` | Regime jurídico (Estatutário, Celetista) |
| `Lotacao` | Lotação no TJDFT |
| `NuOficioInicialProcedimento` | Nº do ofício inicial |
| `DtInicioCessaoJul` | Data início da atividade (YYYY-MM-DD) |

---

### `GET /tlp/1/:mes/:ano` — Tabela de Lotação (TLP1) — Unidades Judiciárias

```
GET https://rest-rh.tjdft.jus.br/api/transparencia/tlp/1/{mes}/{ano}
```

Lotação das unidades judiciárias de 1º e 2º graus.

| Campo | Descrição |
|---|---|
| `TLP` | Código `"TLP1"` |
| `DataReferencia` | Data de referência (YYYY-MM-DD) |
| `Grau` | Grau de jurisdição |
| `Tipo` | Tipo de unidade (VARA, TURMA, GABINETE...) |
| `CdLocalizacao` | Código da localização |
| `DescricaoCompleta` | Nome completo da unidade |
| `LotacaoParadigma` | Lotação estabelecida (referência) |
| `LR_Efet` | Lotação real — servidores efetivos |
| `LR_I` | Lotação real — cedidos/requisitados |
| `LR_SV` | Lotação real — sem vínculo (comissionados) |
| `QtdCJ01`..`QtdCJ04` | Qtd. cargos comissionados CJ-01 a CJ-04 |
| `QtdFC01`..`QtdFC05` | Qtd. funções de confiança FC-01 a FC-05 |

---

### `GET /tlp/2/:mes/:ano` — Tabela de Lotação (TLP2) — Apoio Direto

```
GET https://rest-rh.tjdft.jus.br/api/transparencia/tlp/2/{mes}/{ano}
```

Mesma estrutura da TLP1, com `TLP: "TLP2"`. Cobre unidades de apoio direto à atividade judicante.

---

### `GET /tlp/3/:mes/:ano` — Tabela de Lotação (TLP3) — Apoio Indireto

```
GET https://rest-rh.tjdft.jus.br/api/transparencia/tlp/3/{mes}/{ano}
```

Mesma estrutura, com `TLP: "TLP3"`. Cobre Corregedoria, Secretarias e demais unidades administrativas.

---

### `GET /matrizCargos` — Matriz de Cargos Efetivos

```
GET https://rest-rh.tjdft.jus.br/api/transparencia/matrizCargos
GET https://rest-rh.tjdft.jus.br/api/transparencia/matrizCargos?cargo=ANA022
GET https://rest-rh.tjdft.jus.br/api/transparencia/matrizCargos?localizacao=11201100000
GET https://rest-rh.tjdft.jus.br/api/transparencia/matrizCargos?cargo=ANA022&localizacao=11201100000
```

**Parâmetros opcionais (query string):** `cargo`, `localizacao` (sem ambos = retorna tudo)

| Campo | Descrição |
|---|---|
| `Localizacao` | Código da localização |
| `SgLocalizacao` | Sigla da localização |
| `unidade` | Descrição da localização |
| `grupamentoCNJ` | Grupamento de atuação |
| `codCargo` | Código do cargo (ex: `ANA022`) |
| `desCargo` | Descrição do cargo |
| `area` | Área de atuação |
| `especialidade` | Especialidade |
| `Finalistico` | Se é cargo finalístico (bool) |

---

## Resumo de Todos os Endpoints

| # | API | Método | URL |
|---|---|---|---|
| 1a | Jurisprudência Metadados | GET | `https://jurisdf.tjdft.jus.br/api/v1/pesquisa` |
| 1b | Jurisprudência Pesquisa | POST | `https://jurisdf.tjdft.jus.br/api/v1/pesquisa` |
| 2.1 | Teletrabalho | GET | `.../teletrabalho` |
| 2.2 | Estagiários | GET | `.../estagiarios` |
| 2.3 | Cedidos TJDFT→outros | GET | `.../cedidos/1/{mes}/{ano}` |
| 2.4 | Cedidos outros→TJDFT | GET | `.../cedidos/2/{mes}/{ano}` |
| 2.5 | Anistiados | GET | `.../cedidos/3/{mes}/{ano}` |
| 2.6 | Não Integrantes | GET | `.../servidoresNaoIntegrantes` |
| 2.7 | TLP1 Judiciárias | GET | `.../tlp/1/{mes}/{ano}` |
| 2.8 | TLP2 Apoio Direto | GET | `.../tlp/2/{mes}/{ano}` |
| 2.9 | TLP3 Apoio Indireto | GET | `.../tlp/3/{mes}/{ano}` |
| 2.10 | Matriz de Cargos | GET | `.../matrizCargos[?cargo=&localizacao=]` |

> Base RH: `https://rest-rh.tjdft.jus.br/api/transparencia`

---

## Notas para Agentes de IA

1. **Antes de filtrar por relator:** verificar se o nome existe via GET /pesquisa → campo `relatores` (busca por substring)
2. **Nome não encontrado na lista:** magistrado é provavelmente de 1ª instância — buscar via `processo` ou `query`
3. **`query` pode ser vazio `""`** quando o objetivo é filtrar por relator/órgão sem tema específico
4. **Paginação começa em `0`**, não em 1
5. **Filtro por data não funciona** — `dataJulgamento`/`dataPublicacao` causam erro 500
6. **Decisões monocráticas** têm estrutura diferente — verificar `subbase` antes de acessar campos específicos
7. **APIs de RH** não exigem autenticação e retornam apenas `Nome` nos endpoints de teletrabalho/estagiários
8. **APIs de cedidos e TLP** permitem consultas históricas informando `mes` e `ano`
