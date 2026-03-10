# Quick Wins Features - Revised Plan

**Created:** 2026-03-10
**Revised:** 2026-03-10 (addresses Architect/Critic feedback)
**Complexity:** MEDIUM
**Scope:** 3 new features, 5 new files, modifications to existing schemas

---

## Context

This plan implements 3 "quick win" features for the TJDFT API search functionality:

1. **Text Density Indicator** - Shows how much text a decision has (light/medium/heavy)
2. **Keyword Highlighting** - Marks search terms in decision text
3. **Decision Similarity Filter** - Post-processing filter to show only decisions similar to a reference

**Original plan issues addressed:**
- OCP violation: schemas now inherit from existing `DecisaoBase`
- SRP violation: enrichment logic separated from filtering logic
- Wrong location: `enriquecimento_service.py` in `app/services/`, not `utils/`
- Missing count: response includes both `total` (pre-filter) and `total_filtrado` (post-filter)
- Extra round trips: metadata cached with 24h TTL
- Pagination warning: explicit documentation about post-filter pagination behavior

---

## RALPLAN-DR Summary

### Principles (5)
1. **Inheritance over duplication** -- extend `DecisaoBase` rather than duplicating fields
2. **Separation of concerns** -- enrichment (business logic) in services, filtering (utility) in utils
3. **Transparency in counts** -- always show both pre-filter and post-filter totals
4. **Metadata efficiency** -- cache reference data (relatores list) for 24h
5. **Pagination honesty** -- document that filtering happens client-side, affecting total pages

### Decision Drivers (top 3)
1. **Code maintainability** -- avoid OCP/SRP violations that cause future bugs
2. **User trust** -- be transparent about what filtering does to result counts
3. **API efficiency** -- minimize unnecessary metadata calls

### Viable Options

**Option A: Post-processing with transparency (RECOMMENDED)**
- Fetch from API, apply filters client-side, return both counts
- Pros: Quick to implement, works within existing API constraints
- Cons: Pagination behaves unexpectedly (page 2 may have fewer items)
- Mitigation: Explicit warning in docs + `total_filtrado` field

**Option B: Fetch-all-then-filter**
- Fetch all pages up front, filter entire dataset, re-paginate
- Pros: Correct pagination, accurate counts
- Cons: Slow on large result sets, wastes API quota
- Verdict: Rejected for "quick wins" scope -- acceptable compromise

**Option C: Server-side filtering via API parameters**
- Wait for TJDFT API to add similarity/density filters
- Pros: Proper pagination, no wasted quota
- Cons: Not available, blocked on external API
- Verdict: Not viable -- API doesn't support these filters

---

## Guardrails

### Must Have
- Schemas inherit from `DecisaoBase` (no field duplication)
- `app/services/enriquecimento_service.py` (NOT in utils/)
- `app/utils/filtros_avancados.py` (filtering utilities)
- `app/utils/densidade.py` (density calculation utility)
- Response includes both `total` and `total_filtrado`
- Metadata caching with 24h TTL for relator validation
- Explicit pagination warning in endpoint docs

### Must NOT Have
- No `DecisaoResumida`/`DecisaoDetalhada` with duplicated fields from `DecisaoBase`
- No enrichment logic in `utils/` (business logic belongs in `services/`)
- No filtering logic mixed with enrichment logic
- No metadata API calls on every search (use cache)

---

## File Structure

```
app/
├── schemas/
│   ├── decisao.py          # MODIFY: Add BuscaResponse, DecisaoResumida inheriting from DecisaoBase
│   └── busca.py            # NEW: BuscaRequest, BuscaComFiltrosRequest
├── services/
│   ├── enriquecimento_service.py  # NEW: add_density_indicator, add_keyword_highlights
│   └── busca_service.py    # MODIFY: Use enrichment service
├── utils/
│   ├── densidade.py        # NEW: calculate_density, get_density_category
│   └── filtros_avancados.py # NEW: filter_by_similarity, filter_by_density
└── api/v1/endpoints/
    └── busca.py            # NEW: /busca, /busca/com-filtros endpoints
```

---

## Task Flow (5 Steps)

### Step 1: Create density utility module

**File:** `app/utils/densidade.py`

**Details:**
Pure utility module with no business logic dependencies.

```python
from enum import Enum
from typing import Dict, Any

class DensityCategory(str, Enum):
    LEVE = "leve"      # < 500 chars
    MEDIA = "media"     # 500-2000 chars
    Pesada = "pesada"   # > 2000 chars

def calculate_text_density(registro: Dict[str, Any]) -> int:
    \"\"\"Calculate total character count of decision text.

    Counts ementa + inteiro_teor if available.
    \"\"\"
    count = 0
    if registro.get("ementa"):
        count += len(registro["ementa"])
    if registro.get("inteiro_teor"):
        count += len(registro["inteiro_teor"])
    return count

def get_density_category(density: int) -> DensityCategory:
    \"\"\"Map density count to category.\"\"\"
    if density < 500:
        return DensityCategory.LEVE
    if density < 2000:
        return DensityCategory.MEDIA
    return DensityCategory.PESADA
```

**Acceptance Criteria:**
- [ ] `calculate_text_density({})` returns 0
- [ ] `calculate_text_density({"ementa": "abc"})` returns 3
- [ ] `get_density_category(100)` returns `DensityCategory.LEVE`
- [ ] `get_density_category(1500)` returns `DensityCategory.MEDIA`
- [ ] `get_density_category(5000)` returns `DensityCategory.PESADA`

---

### Step 2: Create advanced filtering utility

**File:** `app/utils/filtros_avancados.py`

**Details:**
Pure filtering functions - no enrichment, no API calls.

```python
from typing import List, Dict, Any, Callable
from app.utils.densidade import DensityCategory, calculate_text_density, get_density_category

def filter_by_similarity(
    registros: List[Dict[str, Any]],
    referencia: Dict[str, Any],
    min_match_score: float = 0.3
) -> List[Dict[str, Any]]:
    \"\"\"Filter decisions by similarity to a reference decision.

    Similarity based on shared relator, classe, or orgao_julgador.
    \"\"\"
    result = []
    for reg in registros:
        score = 0.0
        if reg.get("relator") == referencia.get("relator") and referencia.get("relator"):
            score += 0.5
        if reg.get("classe") == referencia.get("classe") and referencia.get("classe"):
            score += 0.3
        if reg.get("orgao_julgador") == referencia.get("orgao_julgador") and referencia.get("orgao_julgador"):
            score += 0.2
        if score >= min_match_score:
            result.append(reg)
    return result

def filter_by_density(
    registros: List[Dict[str, Any]],
    categorias: List[DensityCategory]
) -> List[Dict[str, Any]]:
    \"\"\"Filter decisions by text density category.\"\"\"
    result = []
    for reg in registros:
        density = calculate_text_density(reg)
        category = get_density_category(density)
        if category in categorias:
            result.append(reg)
    return result

def filter_by_custom(
    registros: List[Dict[str, Any]],
    predicate: Callable[[Dict[str, Any]], bool]
) -> List[Dict[str, Any]]:
    \"\"\"Filter decisions by a custom predicate function.\"\"\"
    return [r for r in registros if predicate(r)]
```

**Acceptance Criteria:**
- [ ] `filter_by_similarity([], ref)` returns empty list
- [ ] `filter_by_similarity` matches on relator (50% score)
- [ ] `filter_by_similarity` matches on classe (30% score)
- [ ] `filter_by_density` correctly filters by category
- [ ] `filter_by_custom` works with lambda predicates

---

### Step 3: Create enrichment service (business logic)

**File:** `app/services/enriquecimento_service.py`

**Details:**
Business logic for enriching decision records. Uses `densidade.py` utility.

```python
import logging
from typing import List, Dict, Any, Optional
from app.utils.densidade import calculate_text_density, get_density_category, DensityCategory

logger = logging.getLogger(__name__)

class EnriquecimentoService:
    \"\"\"Service for enriching decision records with metadata.\"\"\"

    def __init__(self, cache_manager):
        self.cache = cache_manager

    def add_density_indicator(self, registro: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Add text density metadata to a single decision.\"\"\"
        density = calculate_text_density(registro)
        category = get_density_category(density)
        return {
            **registro,
            "densidade": {
                "caracteres": density,
                "categoria": category.value,
            }
        }

    def add_density_indicators(self, registros: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        \"\"\"Add density indicators to all decisions.\"\"\"
        return [self.add_density_indicator(r) for r in registros]

    def add_keyword_highlights(
        self,
        registro: Dict[str, Any],
        keywords: List[str]
    ) -> Dict[str, Any]:
        \"\"\"Add keyword highlighting info to a decision.

        Returns list of keywords found with their positions.
        \"\"\"
        highlights = []
        text = registro.get("ementa", "") or ""

        for keyword in keywords:
            if keyword.lower() in text.lower():
                highlights.append({
                    "termo": keyword,
                    "encontrado": True
                })
            else:
                highlights.append({
                    "termo": keyword,
                    "encontrado": False
                })

        return {
            **registro,
            "destaques": {
                "keywords": highlights
            }
        }

    def add_similarity_info(
        self,
        registro: Dict[str, Any],
        referencia: Dict[str, Any]
    ) -> Dict[str, Any]:
        \"\"\"Add similarity score relative to a reference decision.\"\"\"
        score = 0.0
        matches = []

        if registro.get("relator") == referencia.get("relator") and referencia.get("relator"):
            score += 0.5
            matches.append("relator")
        if registro.get("classe") == referencia.get("classe") and referencia.get("classe"):
            score += 0.3
            matches.append("classe")
        if registro.get("orgao_julgador") == referencia.get("orgao_julgador") and referencia.get("orgao_julgador"):
            score += 0.2
            matches.append("orgao_julgador")

        return {
            **registro,
            "similaridade": {
                "score": round(score, 2),
                "matches": matches
            }
        }
```

**Acceptance Criteria:**
- [ ] `add_density_indicator` returns dict with `densidade.caracteres` and `densidade.categoria`
- [ ] `add_density_indicators` processes list without mutation
- [ ] `add_keyword_highlights` correctly finds keywords in text
- [ ] `add_similarity_info` calculates correct scores (0.5 + 0.3 + 0.2 pattern)

---

### Step 4: Create response schemas (inherit from DecisaoBase)

**File:** `app/schemas/decisao.py` (MODIFY)

**Details:**
Add new schemas that INHERIT from `DecisaoBase` to avoid OCP violation.

```python
# Add to existing decisao.py

class DecisaoResumida(DecisaoBase):
    """Extended decision schema for search results with enrichment."""

    densidade: Optional[DensidadeInfo] = Field(
        None, description="Text density metadata"
    )
    destaques: Optional[DestaqueInfo] = Field(
        None, description="Keyword highlighting info"
    )
    similaridade: Optional[SimilaridadeInfo] = Field(
        None, description="Similarity to reference decision"
    )


class DensidadeInfo(BaseModel):
    """Text density information."""
    caracteres: int = Field(..., description="Character count")
    categoria: str = Field(..., description="Category: leve, media, or pesada")


class DestaqueInfo(BaseModel):
    """Keyword highlighting information."""
    keywords: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of keywords with found status"
    )


class SimilaridadeInfo(BaseModel):
    """Similarity information."""
    score: float = Field(..., ge=0, le=1, description="Similarity score 0-1")
    matches: List[str] = Field(
        default_factory=list, description="Fields that matched"
    )


class BuscaResponse(BaseModel):
    """Response schema for search with filtering."""

    resultados: List[DecisaoResumida]
    total: int = Field(..., description="Total results from API (pre-filter)")
    total_filtrado: int = Field(..., description="Results after filtering")
    pagina: int = Field(..., description="Current page number")
    tamanho: int = Field(..., description="Requested page size")
    consulta_id: str = Field(..., description="Query ID for reference")
```

**Acceptance Criteria:**
- [ ] `DecisaoResumida` inherits from `DecisaoBase` (no duplicate fields)
- [ ] `DecisaoResumida` includes optional enrichment fields
- [ ] `BuscaResponse` has both `total` and `total_filtrado`
- [ ] All schemas have proper Pydantic Field descriptions

---

### Step 5: Create endpoint with metadata caching

**File:** `app/api/v1/endpoints/busca.py` (NEW)

**Details:**
FastAPI router with caching for metadata.

```python
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from app.schemas.decisao import BuscaResponse, DecisaoResumida
from app.services.busca_service import BuscaService
from app.services.enriquecimento_service import EnriquecimentoService
from app.services.tjdft_client import TJDFTClient
from app.utils.filtros_avancados import filter_by_similarity, filter_by_density, DensityCategory
from app.utils.cache import CacheManager
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/busca", tags=["busca"])

# Cache metadata for 24h
METADATA_CACHE_TTL = 86400

@router.post("", response_model=BuscaResponse)
async def buscar_decisoes(
    query: str = Query(..., min_length=1, description="Search query"),
    pagina: int = Query(1, ge=1, description="Page number"),
    tamanho: int = Query(20, ge=1, le=40, description="Page size (max 40)"),
    adicionar_densidade: bool = Query(False, description="Add text density info"),
    destacar_keywords: Optional[List[str]] = Query(None, description="Keywords to highlight"),
    filtros_similaridade_uuid: Optional[str] = Query(None, description="Filter by similarity to this UUID"),
    filtros_densidade: Optional[List[DensityCategory]] = Query(None, description="Filter by density categories"),
    session: AsyncSession = Depends(get_db),
):
    \"\"\"
    Search decisions with optional enrichment and filtering.

    **WARNING:** Filtering is applied client-side AFTER pagination.
    This means:
    - `total_filtrado` may be less than `tamanho` on non-first pages
    - `total_filtrado` reflects count AFTER filters are applied
    - For complete filtered results, consider fetching all pages

    Example: If you request page 2 (items 21-40) and filter removes 15 items,
    you'll receive only 5 items but `total_filtrado` will show the true count.
    \"\"\"
    cache = CacheManager()

    # 1. Get active relators list (cached 24h)
    relatores_ativos = await _get_relatores_ativos(cache, session)

    # 2. Execute search via BuscaService
    busca_svc = BuscaService(session, cache)
    resultado_bruto = await busca_svc.buscar(
        BuscaRequest(query=query, pagina=pagina, tamanho=tamanho),
        usuario_id=None
    )

    # 3. Apply enrichment
    enriquecimento_svc = EnriquecimentoService(cache)
    resultados = resultado_bruto["resultados"]

    if adicionar_densidade:
        resultados = enriquecimento_svc.add_density_indicators(resultados)

    if destacar_keywords:
        resultados = [
            enriquecimento_svc.add_keyword_highlights(r, destacar_keywords)
            for r in resultados
        ]

    # 4. Apply filtering (client-side)
    total_pre_filtro = len(resultados)

    if filtros_similaridade_uuid:
        # Get reference decision
        ref_decisao = await busca_svc.busca_similares(filtros_similaridade_uuid, limite=1)
        if ref_decisao:
            resultados = filter_by_similarity(resultados, ref_decisao[0])

    if filtros_densidade:
        resultados = filter_by_density(resultados, filtros_densidade)

    total_pos_filtro = len(resultados)

    # 5. Build response
    return BuscaResponse(
        resultados=[DecisaoResumida(**r) for r in resultados],
        total=resultado_bruto["total"],  # Pre-filter count from API
        total_filtrado=total_pos_filtro,  # Post-filter count
        pagina=pagina,
        tamanho=tamanho,
        consulta_id=resultado_bruto["consulta_id"]
    )


async def _get_relatores_ativos(cache: CacheManager, session: AsyncSession) -> List[str]:
    \"\"\"Get list of active relators (cached 24h).\"\"\"
    cache_key = "relatores_ativos"

    # Try cache first
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Fetch from API
    async with TJDFTClient(cache) as client:
        metadata = await client.get_metadata()
        relatores = [r["nome"] for r in metadata.get("relatores", [])]

    # Cache for 24h
    cache.set(cache_key, relatores, ttl=METADATA_CACHE_TTL)
    return relatores
```

**Acceptance Criteria:**
- [ ] Endpoint accepts all query parameters
- [ ] `total_filtrado` correctly reflects post-filter count
- [ ] Metadata is cached (second call doesn't hit API)
- [ ] Warning in docstring about pagination behavior
- [ ] Returns `BuscaResponse` with proper schema

---

## Implementation Sequence

```
Step 1: densidade.py (no dependencies)
Step 2: filtros_avancados.py (depends on: densidade.py)
Step 3: enriquecimento_service.py (depends on: densidade.py)
Step 4: decisao.py schema modification (no dependencies)
Step 5: busca.py endpoint (depends on: all above)
```

---

## Success Criteria

1. [ ] `DecisaoResumida` inherits from `DecisaoBase` (verified via `__mro__`)
2. [ ] `app/services/enriquecimento_service.py` exists (not in `utils/`)
3. [ ] `app/utils/filtros_avancados.py` exists (pure filtering, no enrichment)
4. [ ] Response includes both `total` and `total_filtrado`
5. [ ] `total_filtrado` equals length of filtered results
6. [ ] Metadata (relatores list) cached for 24h
7. [ ] Second search within 24h uses cached metadata (verified via logs)
8. [ ] Endpoint docstring includes pagination warning
9. [ ] All tests pass

---

## ADR

- **Decision:** Implement quick wins with post-processing pattern, transparency via dual counts, and proper separation of concerns
- **Drivers:** Code maintainability (OCP/SRP), user trust (transparent counts), API efficiency (metadata caching)
- **Alternatives considered:**
  - Fetch-all-then-filter: Rejected due to performance impact on large result sets
  - Server-side filtering: Rejected because TJDFT API doesn't support these filters
  - Skip filtering feature: Rejected because user value outweighs pagination quirk
- **Why chosen:** Post-processing with `total_filtrado` field provides immediate user value while being transparent about limitations. Proper separation (services vs utils) addresses architectural concerns.
- **Consequences:**
  - Positive: Features delivered quickly, code is maintainable, users understand filtering impact
  - Negative: Pagination behavior may confuse users (mitigated by warning docs)
  - Technical debt: Future consideration for true server-side filtering when API supports it
- **Follow-ups:** Monitor user feedback; if pagination confusion is high, consider fetch-all approach or wait for API support

---

## Schema Inheritance Pattern (Code Snippet)

```python
# CORRECT: Inheritance from DecisaoBase
class DecisaoResumida(DecisaoBase):
    """Extended with enrichment fields only."""
    densidade: Optional[DensidadeInfo] = None
    destaques: Optional[DestaqueInfo] = None
    similaridade: Optional[SimilaridadeInfo] = None

# WRONG: Duplicating fields (OCP violation)
class DecisaoResumida(BaseModel):
    """DO NOT DO THIS."""
    uuid_tjdft: str  # Duplicate!
    processo: Optional[str]  # Duplicate!
    ementa: Optional[str]  # Duplicate!
    # ... all DecisaoBase fields duplicated ...
    densidade: Optional[DensidadeInfo] = None  # Only new field
```

---

## Open Questions

1. [ ] Should keyword highlighting support case-insensitive matching only, or also regex patterns?
2. [ ] What should be the default `min_match_score` for similarity filtering? (Currently 0.3)
3. [ ] Should we add a "fetch all pages" option for users who want complete filtered results?

(These will be written to `.omc/plans/open-questions.md` after plan approval)
