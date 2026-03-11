# TJDFT Analytics CLI - Work Plan

**Created:** 2026-03-10
**Complexity:** MEDIUM-HIGH
**Scope:** 7 new files in `tjdft_analytics/`, standalone CLI package

---

## Context

The existing `tjdft-api` project has an async FastAPI server with `TJDFTClient` (async, httpx, Redis cache). The new CLI is a **standalone tool** that lives in `tjdft_analytics/` within the same repo but uses **synchronous httpx** (no async needed for CLI) and **local JSON file cache** (no Redis dependency). The CLI does not import from `app/` -- it is self-contained.

Key API facts already validated in `app/services/tjdft_client.py`:
- POST `https://jurisdf.tjdft.jus.br/api/v1/pesquisa` with `{query, pagina, tamanho, termosAcessorios}`
- GET same URL returns metadata (relatores, classes, orgaos)
- Pagination is 0-indexed, max 40 per page
- Fields that cause 400: `revisor`, `relatorDesignado`, `segredoJustica`, `dataJulgamento`, etc.
- `decisoes-monocraticas` subbase lacks `decisao`, `dataJulgamento`, `relatorAtivo`, `turmaRecursal`

---

## RALPLAN-DR Summary

### Principles (5)
1. **Standalone CLI** -- no dependency on the FastAPI app; independent `requirements.txt`
2. **API-first classification** -- use `decisao` field when available, fallback to `ementa`, never rely solely on `inteiroTeor`
3. **Aggregation-first strategy** -- use API aggregations (tamanho=1) for counts/rankings, paginate only when classification is needed
4. **Bounded resource usage** -- max 3 pages (120 records) per relator in rankings; 0.3s rate limit between pages
5. **Three-category output** -- always show deferido/indeferido/inconclusivo; never collapse inconclusivo

### Decision Drivers (top 3)
1. **Accuracy of classification** -- the classifier is the core value proposition; false positives undermine trust
2. **API rate respect** -- the TJDFT API has rate limits; aggressive pagination will get blocked
3. **User experience** -- Rich tables + plotext graphs make the CLI immediately useful without a browser

### Viable Options

**Option A: Standalone sync CLI (RECOMMENDED)**
- Sync httpx client, local JSON cache, no dependency on `app/`
- Pros: zero setup friction, works without Redis/DB, portable
- Cons: duplicates some HTTP logic from `tjdft_client.py`

**Option B: Reuse existing async client via wrapper**
- Import `TJDFTClient` from `app/`, wrap with `asyncio.run()`
- Pros: DRY, shares cache/retry logic
- Cons: requires Redis or CacheManager setup, couples CLI to server dependencies, heavier install

Option B invalidated because: the CLI must work standalone without Redis, database, or FastAPI dependencies. The sync httpx client is ~80 lines and trivial to maintain independently.

---

## Guardrails

### Must Have
- All 5 CLI commands working: `relator`, `comparar`, `turma`, `tema`, `cruzamento`
- Classifier with explicit test against known decisions before analytics use
- Cache with TTL enforcement (stale files deleted, not served)
- Rate limiting (0.3s sleep between paginated requests)
- All output through `visualizacao.py` (no raw `print()`)

### Must NOT Have
- No async code (sync httpx only)
- No imports from `app/` package
- No Redis dependency
- No fields that cause API 400 errors in requests
- No pagination beyond 3 pages per relator in ranking analyses

---

## Task Flow (6 Steps)

### Step 1: Scaffold + cache.py + requirements.txt

**What:** Create `tjdft_analytics/` directory, `requirements.txt`, and `cache.py`.

**Files:**
- `tjdft_analytics/requirements.txt`
- `tjdft_analytics/cache.py`

**Details:**
- `requirements.txt`: `httpx>=0.27`, `rich>=13.0`, `plotext>=5.2`, `click>=8.0`
- `cache.py`: Read/write JSON files to `~/.tjdft_cache/`. Key = md5 hash of (query + filtros). Each file stores `{"data": ..., "timestamp": epoch}`. On `get()`, check `time.time() - timestamp < 3600`; if expired, delete file and return None. Include `clear_cache()` function.

**Acceptance Criteria:**
- [ ] `from tjdft_analytics.cache import Cache` works
- [ ] `Cache().set("test", {"a": 1})` creates a JSON file in `~/.tjdft_cache/`
- [ ] `Cache().get("test")` returns the data within TTL
- [ ] After manually setting timestamp to 2 hours ago, `get()` returns None
- [ ] `Cache().clear()` removes all files in the cache dir

---

### Step 2: api.py -- Synchronous HTTP client

**What:** Sync httpx client wrapping GET (metadata) and POST (search) to the TJDFT API.

**Files:**
- `tjdft_analytics/api.py`

**Details:**
- Class `TJDFTApi` with sync `httpx.Client` (not AsyncClient)
- Methods: `get_metadata()`, `buscar(query, pagina, tamanho, **filtros)`, `buscar_paginas(query, max_paginas=3, **filtros)`
- `buscar()` builds `termosAcessorios` from kwargs: `relator` -> `nomeRelator`, `classe` -> `descricaoClasseCnj`, `orgao` -> `descricaoOrgaoJulgador`, `base`, `subbase`
- Integrate `cache.py` for all requests
- `buscar_paginas()` sleeps 0.3s between pages, stops when no more results or max reached
- `validar_relator(nome)` -- calls `get_metadata()`, does case-insensitive substring match, returns list of exact matches. If no match, raises `RelatorNaoEncontrado`.
- Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
- Custom exceptions: `ApiError`, `ApiTimeout`, `RelatorNaoEncontrado`

**Acceptance Criteria:**
- [ ] `TJDFTApi().get_metadata()` returns dict with keys `relatores`, `classes`, `orgaos`
- [ ] `TJDFTApi().buscar("dano moral", pagina=0, tamanho=1)` returns dict with `registros`, `total`, `agregacoes`
- [ ] `TJDFTApi().buscar(relator="GEORGE LOPES")` filters by relator correctly
- [ ] Second identical call is served from cache (no HTTP request)
- [ ] `validar_relator("george")` returns `["GEORGE LOPES"]` (or similar matches)
- [ ] `validar_relator("XYZNONEXISTENT")` raises `RelatorNaoEncontrado`

---

### Step 3: classificador.py -- Decision classifier

**What:** Pattern-matching classifier that labels decisions as deferido/indeferido/inconclusivo.

**Files:**
- `tjdft_analytics/classificador.py`
- `tjdft_analytics/test_classificador.py` (inline test script)

**Details:**
- `PADROES_DEFERIDO` and `PADROES_INDEFERIDO` lists as specified
- `normalizar(texto)` -- `lower()` + `unicodedata.normalize("NFD", ...)` to strip accents
- `classificar(registro: dict) -> str`:
  1. If `subbase != "decisoes-monocraticas"`: check `registro["decisao"]` first, then fallback to `registro.get("ementa", "")`
  2. If `subbase == "decisoes-monocraticas"`: check `ementa` first, then `inteiroTeor[:500]`
  3. Normalize text, scan for deferido patterns first, then indeferido
  4. If both match, use the one that appears first in the text
  5. If neither matches, return `"inconclusivo"`
- `classificar_lote(registros: list) -> dict` -- returns `{"deferido": N, "indeferido": N, "inconclusivo": N, "total": N}`

**Acceptance Criteria:**
- [ ] `classificar({"decisao": "DOU PROVIMENTO ao recurso", "subbase": "acordaos"})` returns `"deferido"`
- [ ] `classificar({"decisao": "NEGO PROVIMENTO", "subbase": "acordaos"})` returns `"indeferido"`
- [ ] `classificar({"decisao": "Remetam-se os autos", "subbase": "acordaos"})` returns `"inconclusivo"`
- [ ] `classificar({"ementa": "...provejo parcialmente...", "subbase": "decisoes-monocraticas"})` returns `"deferido"`
- [ ] Accented text ("nao dou provimento" vs "nao dou provimento") handled correctly
- [ ] `classificar_lote()` counts match manual counting of a 10-item list
- [ ] `test_classificador.py` passes with `python test_classificador.py` (no pytest needed)

---

### Step 4: analytics.py -- 5 analysis functions

**What:** The 5 core analyses that combine API calls + classification.

**Files:**
- `tjdft_analytics/analytics.py`

**Details:**

Each function takes an `api: TJDFTApi` instance and returns a structured dict (not formatted output).

1. **`perfil_relator(api, relator, query="")`**
   - Validate relator name via `api.validar_relator()`
   - Fetch with `tamanho=1` to get total + aggregations
   - Fetch up to 3 pages (120 records) for classification
   - Return: `{relator, query, total, classificacao: {deferido, indeferido, inconclusivo}, por_orgao: [{orgao, total, deferido%, ...}], por_classe: [{classe, total, deferido%, ...}]}`

2. **`comparar_relatores(api, relatores: list, query)`**
   - For each relator: validate, fetch aggregation (tamanho=1), fetch 2 pages for classification
   - Return: `{query, relatores: [{nome, total, deferido%, indeferido%, inconclusivo%, amostra_size}]}`
   - Sort by `deferido%` descending

3. **`tema_por_turma(api, query)`**
   - Single search with `tamanho=1` to get `agregacoes.orgaoJulgador`
   - Take top 5 orgaos, for each: search with orgao filter, 2 pages, classify
   - Return: `{query, turmas: [{orgao, total, deferido%, indeferido%, inconclusivo%, amostra}]}`

4. **`top_relatores_tema(api, query, n=10)`**
   - Search with `tamanho=1` to get `agregacoes.relator`
   - Take top N relatores from aggregation
   - For each: fetch 1-2 pages, classify
   - Return: `{query, relatores: [{nome, total_agregacao, amostra_size, deferido%, ...}]}`

5. **`cruzamento_relator_classe(api, relator)`**
   - Validate relator
   - Fetch `tamanho=1` with relator filter to get `agregacoes.classe`
   - For top 5 classes: fetch 2 pages with relator+classe filter, classify
   - Return: `{relator, classes: [{classe, total, deferido%, indeferido%, inconclusivo%, amostra}]}`

**Acceptance Criteria:**
- [ ] Each function returns a dict (not prints anything)
- [ ] `perfil_relator(api, "GEORGE LOPES")` returns dict with all expected keys
- [ ] `comparar_relatores()` result is sorted by `deferido%` descending
- [ ] `tema_por_turma()` returns max 5 turmas
- [ ] `top_relatores_tema(query, n=3)` returns exactly 3 relatores
- [ ] `cruzamento_relator_classe()` returns max 5 classes
- [ ] No function exceeds 3 pages per relator/filter combination
- [ ] No function calls `print()` directly

---

### Step 5: visualizacao.py -- Rich + Plotext output

**What:** Rendering layer that takes analytics dicts and produces formatted terminal output.

**Files:**
- `tjdft_analytics/visualizacao.py`

**Details:**
- Uses `rich.console.Console`, `rich.table.Table`, `rich.panel.Panel`, `rich.progress.Progress`
- Uses `plotext` for horizontal bar charts (deferido% comparisons)
- Functions mirror analytics: `exibir_perfil(data)`, `exibir_comparacao(data)`, `exibir_turmas(data)`, `exibir_ranking(data)`, `exibir_cruzamento(data)`
- Color coding: green for deferido, red for indeferido, yellow for inconclusivo
- Each function takes the dict returned by its analytics counterpart
- `progresso(desc, total)` -- context manager wrapping `rich.progress.Progress` for use during data fetching
- No raw `print()` -- everything through `Console()`

**Acceptance Criteria:**
- [ ] Each `exibir_*` function produces visible output with Rich formatting
- [ ] Tables have proper column headers and alignment
- [ ] Percentages are formatted to 1 decimal place
- [ ] Bar charts render via plotext without errors
- [ ] Color coding is applied (green/red/yellow)
- [ ] Progress bar works during multi-page fetches

---

### Step 6: tjdft_cli.py -- Click CLI entry point

**What:** Click-based CLI wiring all modules together.

**Files:**
- `tjdft_analytics/tjdft_cli.py`

**Details:**
- 5 commands matching the spec:
  - `relator NAME [--tema QUERY]`
  - `comparar NAME1 NAME2 [NAME3...] --tema QUERY`
  - `turma --tema QUERY`
  - `tema QUERY [--top N]`
  - `cruzamento --relator NAME [--por classe]`
- Global error handler: catch `ApiError` -> "API indisponivel, tente novamente", `ApiTimeout` -> "Timeout na conexao", `RelatorNaoEncontrado` -> "Relator X nao encontrado. Similares: [...]"
- `--limpar-cache` flag to clear cache before running
- `--sem-grafico` flag to skip plotext charts (tables only)
- Wrap analytics calls with `visualizacao.progresso()` for progress feedback

**Acceptance Criteria:**
- [ ] `python tjdft_cli.py relator "GEORGE LOPES"` shows profile with classification breakdown
- [ ] `python tjdft_cli.py comparar "ANA CANTARINO" "CARMEN BITTENCOURT" --tema "dano moral"` shows comparison table
- [ ] `python tjdft_cli.py turma --tema "improbidade administrativa"` shows turma breakdown
- [ ] `python tjdft_cli.py tema "locacao comercial" --top 5` shows top 5 relatores
- [ ] `python tjdft_cli.py cruzamento --relator "JAIR SOARES" --por classe` shows class breakdown
- [ ] Invalid relator name shows error with suggestions
- [ ] `--limpar-cache` clears cache before executing
- [ ] `--sem-grafico` suppresses plotext output
- [ ] `--help` shows usage for each command

---

## Implementation Order and Dependencies

```
Step 1: cache.py + requirements.txt     (no dependencies)
Step 2: api.py                          (depends on: cache.py)
Step 3: classificador.py                (no dependencies, can parallel with Step 2)
Step 4: analytics.py                    (depends on: api.py + classificador.py)
Step 5: visualizacao.py                 (no dependencies on analytics, can parallel with Step 4)
Step 6: tjdft_cli.py                    (depends on: all above)
```

Recommended parallel lanes:
- Lane A: Step 1 -> Step 2 -> Step 4 -> Step 6
- Lane B: Step 3 (with tests, in parallel with Steps 1-2)
- Lane C: Step 5 (in parallel with Step 4)

---

## Classifier Verification Strategy

Before running analytics (Step 4), verify the classifier independently:

1. **Unit tests in `test_classificador.py`** (Step 3) -- 10+ hardcoded cases covering:
   - Clear deferido/indeferido patterns
   - Accented vs unaccented text
   - Monocraticas without `decisao` field
   - Conflicting patterns (both match -> positional resolution)
   - Empty/None fields -> inconclusivo

2. **Live validation script** (run manually after Step 3):
   ```bash
   # Fetch 40 real decisions and classify them
   python -c "
   from api import TJDFTApi
   from classificador import classificar, classificar_lote
   api = TJDFTApi()
   r = api.buscar('dano moral', tamanho=40)
   stats = classificar_lote(r['registros'])
   print(stats)
   # Expect: inconclusivo < 40% for acordaos
   "
   ```

3. **Acceptance threshold**: For acordaos with `decisao` field populated, inconclusivo rate should be < 30%. If higher, expand pattern lists before proceeding to Step 4.

---

## Error Handling Strategy

| Scenario | Where Handled | Behavior |
|---|---|---|
| API unreachable | `api.py` retry loop | 3 retries with backoff, then raise `ApiError` |
| API returns 400 | `api.py` | Raise `ApiError` with response body (likely bad filter field) |
| API returns 500 | `api.py` retry loop | Retry up to 3 times, then raise `ApiError` |
| Relator not found | `api.validar_relator()` | Raise `RelatorNaoEncontrado` with fuzzy suggestions |
| Empty results | `analytics.py` | Return zeroed stats dict, never crash |
| Cache file corrupted | `cache.py` | Delete corrupted file, return None (cache miss) |
| Rate limit (429) | `api.py` | Sleep 2s and retry (counted in retry budget) |
| No internet | `api.py` | `httpx.ConnectError` -> `ApiError("Sem conexao")` |
| Plotext not installed | `visualizacao.py` | Graceful fallback to Rich-only tables |

All exceptions bubble up to `tjdft_cli.py` which catches them and shows user-friendly messages via Rich console (red panel with error description).

---

## Success Criteria

1. All 5 CLI commands execute end-to-end against the live TJDFT API
2. Classifier inconclusivo rate < 30% on acordaos sample
3. Cache prevents duplicate HTTP requests within 1 hour
4. No command takes more than 30 seconds (bounded by 3-page limit)
5. Output is formatted with Rich tables and plotext charts
6. Error scenarios show user-friendly messages (not stack traces)
7. `tjdft_analytics/` is self-contained -- no imports from `app/`
