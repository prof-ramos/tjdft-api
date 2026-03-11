# TJDFT API - Quick Wins Features (Revised Implementation Plan)

**Plan ID:** tjdft-quick-wins-revised
**Created:** 2025-03-10
**Status:** Draft - Iteration 4 (Final Fixes Applied)
**Complexity:** MEDIUM

---

## Context

This plan implements four "quick wins" features for the TJDFT API search functionality, addressing architect feedback from the previous revision. The features use existing TJDFT API response fields and require minimal changes to the codebase while following SOLID principles.

### Architect Concerns Addressed

1. **OCP Violation** - Schemas will inherit from `DecisaoBase` instead of duplicating fields
2. **SRP Violation** - Enrichment logic separated from filtering logic
3. **Wrong location** - Business logic in `services/`, utilities in `utils/`
4. **Missing count** - Response includes both `total` (pre-filter) and `total_filtrado` (post-filter)
5. **Extra round trips** - Metadata cached with 24h TTL

---

## Features to Implement

### Feature #3: Alerta de Densidade de Precedentes
- **Field:** `hits.value` from TJDFT API response
- **Categories:**
  - `escasso`: < 20 resultados
  - `moderado`: 20-499 resultados
  - `consolidado`: 500-4999 resultados
  - `massivo`: >= 5000 resultados
- **Output:** Add `densidade` object to response with category and alert message

### Feature #4: Segregação de Instância
- **Fields:** `turmaRecursal` (bool) and `subbase` (string)
- **Logic:** Calculate `instancia` value:
  - `"juizado_especial"` when `turmaRecursal=true` or `subbase="acordaos-tr"`
  - `"tjdft_2a_instancia"` otherwise
- **Query param:** `?excluir_turmas_recursais=true` to filter out results

### Feature #5: Filtro de Relatores Ativos
- **Field:** `relatorAtivo` (boolean) from TJDFT API response
- **Query param:** `?apenas_ativos=true` to filter only active relatores
- **Implementation:** Post-processing filter (not sent to TJDFT API)

### Feature #6: Triagem Rápida por Marcadores
- **Field:** `marcadores` (dict) from TJDFT API response
- **List view:** Promote as `resumo_relevancia` (shows highlighted snippets)
- **Detail view:** Full ementa shown only on detail endpoint (future)

---

## File Structure

### New Files

| File | Purpose |
|------|---------|
| `app/utils/enrichment.py` | Enrichment logic (density, instance calculation) |
| `app/utils/filtros.py` (add NEW functions) | Add post-processing filters (active relator, instance) |
| `app/api/v1/endpoints/busca.py` | Search endpoints |
| `tests/test_utils/test_enrichment.py` | Tests for enrichment utilities |
| `tests/test_api/test_busca.py` | Tests for search endpoints |

### Modified Files

| File | Changes |
|------|---------|
| `app/schemas/consulta.py` | Add new request/response fields |
| `app/schemas/decisao.py` | Add enriched response schemas inheriting from `DecisaoBase` |
| `app/services/busca_service.py` | Add enrichment and filtering to `buscar()` method |
| `app/main.py` | Register new router |
| `app/utils/cache.py` | Add metadata caching constant |

---

## Implementation Steps

### Step 1: Create Enrichment Utilities

**File:** `app/utils/enrichment.py`

```python
"""Enrichment utilities for TJDFT API responses."""

from typing import Dict, Any, Optional
from enum import Enum


class DensidadeCategoria(str, Enum):
    """Categories for precedent density."""
    ESCASSO = "escasso"
    MODERADO = "moderado"
    CONSOLIDADO = "consolidado"
    MASSIVO = "massivo"


class InstanciaTipo(str, Enum):
    """Types of judicial instance."""
    JUIZADO_ESPECIAL = "juizado_especial"
    TJDFT_2A_INSTANCIA = "tjdft_2a_instancia"


def calcular_densidade(total: int) -> Dict[str, Any]:
    """
    Calculate density category based on total hits.

    Args:
        total: Total number of results from hits.value

    Returns:
        Dict with categoria and alerta fields
    """
    if total < 20:
        categoria = DensidadeCategoria.ESCASSO
        alerta = "Poucos precedentes encontrados. Considere ampliar os termos de busca."
    elif total < 500:
        categoria = DensidadeCategoria.MODERADO
        alerta = "Quantidade moderada de precedentes."
    elif total < 5000:
        categoria = DensidadeCategoria.CONSOLIDADO
        alerta = "Tema bem consolidado nos precedentes."
    else:
        categoria = DensidadeCategoria.MASSIVO
        alerta = "Tema com jurisprudência massiva. Considere filtros adicionais."

    return {
        "categoria": categoria.value,
        "total": total,
        "alerta": alerta
    }


def calcular_instancia(
    turma_recursal: Optional[bool] = None,
    subbase: Optional[str] = None
) -> Optional[str]:
    """
    Calculate instance type from decision metadata.

    Args:
        turma_recursal: Value from turmaRecursal field
        subbase: Value from subbase field

    Returns:
        Instancia type or None if undetermined
    """
    if turma_recursal is True or subbase == "acordaos-tr":
        return InstanciaTipo.JUIZADO_ESPECIAL
    return InstanciaTipo.TJDFT_2A_INSTANCIA


def extrair_marcadores_relevancia(
    marcadores: Optional[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Extract relevant markers from marcadores field for summary view.

    Args:
        marcadores: Raw marcadores dict from TJDFT API

    Returns:
        Simplified dict with highlighted snippets
    """
    if not marcadores:
        return {}

    resumo = {}
    for key, value in marcadores.items():
        if isinstance(value, list) and value:
            # Store first snippet for each field
            resumo[key] = value[0] if isinstance(value[0], str) else str(value[0])
        elif isinstance(value, str):
            resumo[key] = value

    return resumo
```

**Acceptance Criteria:**
- All functions have type hints
- Functions are pure (no side effects)
- Includes docstrings with examples
- Handles None/missing inputs gracefully

---

### Step 2: Update Schemas with Inheritance and Pydantic Aliases

**CRITICAL FIX #1:** Do NOT import `DecisaoBase` from within `decisao.py` - it's defined in that same file.

**CRITICAL FIX #2:** Add Pydantic aliases to `DecisaoBase` to map API field names (e.g., `uuid` -> `uuid_tjdft`, `nomeRelator` -> `relator`).

**CRITICAL FIX #9 (Reversed):** The earlier decision to NOT add `excluir_turmas_recursais` and `apenas_ativos` to `BuscaRequest` was incorrect. These fields MUST be added to support `model_copy()` in the endpoint.

**File:** `app/schemas/decisao.py` (modify existing and add new schemas)

```python
# First, UPDATE DecisaoBase to add field aliases for API mapping
class DecisaoBase(BaseModel):
    """Base schema for decisao with common fields."""

    uuid_tjdft: str = Field(..., alias="uuid", description="TJDFT UUID for the decision")
    processo: Optional[str] = Field(None, alias="numeroProcesso", description="Process number")
    ementa: Optional[str] = Field(None, description="Decision summary (ementa)")
    inteiro_teor: Optional[str] = Field(None, alias="inteiroTeorHtml", description="Full decision text")
    relator: Optional[str] = Field(None, alias="nomeRelator", description="Relator name")
    data_julgamento: Optional[date] = Field(None, alias="dataJulgamento", description="Judgment date")
    data_publicacao: Optional[date] = Field(None, alias="dataPublicacao", description="Publication date")
    orgao_julgador: Optional[str] = Field(None, alias="descricaoOrgaoJulgador", description="Judging body")
    classe: Optional[str] = Field(None, alias="descricaoClasseCnj", description="Process class/type")

    model_config = {"from_attributes": True, "populate_by_name": True}


# Rest of the file remains the same until we add new schemas...

# Add AFTER existing schemas (no import needed - DecisaoBase is defined above)
class DecisaoEnriquecida(DecisaoBase):
    """
    Enriched decision schema for list view.
    Inherits all fields from DecisaoBase (which now has aliases).
    """
    resumo_relevancia: Optional[Dict[str, str]] = Field(
        default=None,
        description="Highlighted snippets from search"
    )
    instancia: Optional[str] = Field(
        default=None,
        description="Instance type (juizado_especial or tjdft_2a_instancia)"
    )
    relator_ativo: Optional[bool] = Field(
        default=None,
        alias="relatorAtivo",
        description="Whether the relator is still active"
    )

    # Note: populate_by_name inherited from DecisaoBase, no need to repeat
    model_config = {"from_attributes": True, "populate_by_name": True}


class DecisaoDetalhe(DecisaoEnriquecida):
    """
    Full detail view with complete ementa.
    Inherits from DecisaoEnriquecida.
    """
    pass  # Full ementa already inherited from DecisaoBase
```

**File:** `app/schemas/consulta.py` (modifications)

**NOTE:** The filter fields (`excluir_turmas_recursais`, `apenas_ativos`) are added to `BuscaRequest` as optional fields to support `model_copy()` in the endpoint (CRITICAL FIX #9). They receive values from query parameters.

```python
# First, UPDATE BuscaRequest to add the filter fields
class BuscaRequest(BaseModel):
    """Request schema for search operations."""

    query: str = Field(..., min_length=1, description="Search query string")
    filtros: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional search filters"
    )
    pagina: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    tamanho: int = Field(
        default=20, ge=1, le=100, description="Results per page (max 100)"
    )
    # FIX #9: Add these optional fields for query parameter support
    excluir_turmas_recursais: Optional[bool] = Field(
        default=None,
        description="Exclude Juizados Especiais (turmas recursais)"
    )
    apenas_ativos: Optional[bool] = Field(
        default=None,
        description="Filter only active relatores"
    )

    model_config = {"from_attributes": True}


# New response schema (add if not exists)
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class BuscaResponseEnriquecida(BaseModel):
    """Enhanced search response with metadata."""

    resultados: List[DecisaoEnriquecida]
    total: int = Field(..., description="Total results before filtering")
    total_filtrado: int = Field(..., description="Total results after filtering")
    pagina: int
    tamanho: int
    consulta_id: str
    densidade: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Precedent density analysis"
    )
```

**Acceptance Criteria:**
- `DecisaoBase` updated with `alias` parameters for all fields that map to API response
- `DecisaoEnriquecida` inherits from `DecisaoBase` (OCP compliance)
- NO import of `DecisaoBase` within `decisao.py` (it's defined there)
- `model_config` includes `populate_by_name: True` for alias support
- Pydantic automatically maps `uuid` -> `uuid_tjdft`, `nomeRelator` -> `relator`, etc.
- FIX #9: `BuscaRequest` includes `excluir_turmas_recursais` and `apenas_ativos` as optional fields

---

### Step 3: Create Post-Processing Filters

**MAJOR FIX #6:** Add guards for missing fields in monocratic decisions.

**FIX #11:** The actual filename is `filtros.py` (not `filters.py`). Add NEW functions to the existing file.

**File:** `app/utils/filtros.py` (add NEW functions to existing file)

```python
# Add to existing filtros.py

def filtrar_por_instancia(
    registros: List[Dict[str, Any]],
    excluir_turmas_recursais: bool
) -> List[Dict[str, Any]]:
    """
    Filter out turmas recursais if requested.

    Args:
        registros: List of decision records
        excluir_turmas_recursais: Whether to exclude juizados especiais

    Returns:
        Filtered list of records

    Note:
        Monocratic decisions (decisoes-monocraticas) may lack
        turmaRecursal and subbase fields - these are handled gracefully
        and will NOT be filtered out.
    """
    if not excluir_turmas_recursais:
        return registros

    filtrados = []
    for r in registros:
        # FIX #6: Handle missing fields - monocratic decisions may not have these
        is_turma_recursal = r.get("turmaRecursal", False)
        subbase = r.get("subbase", "")

        # Only exclude if explicitly marked as turma recursal
        # Missing fields default to keeping the record
        if not is_turma_recursal and subbase != "acordaos-tr":
            filtrados.append(r)

    return filtrados


def filtrar_relatores_ativos(
    registros: List[Dict[str, Any]],
    apenas_ativos: bool
) -> List[Dict[str, Any]]:
    """
    Filter to include only active relatores.

    Args:
        registros: List of decision records
        apenas_ativos: Whether to filter only active relatores

    Returns:
        Filtered list of records

    Note:
        Monocratic decisions may lack relatorAtivo field.
        Records with missing relatorAtivo are EXCLUDED when filtering
        for active relatores (conservative approach).
    """
    if not apenas_ativos:
        return registros

    filtrados = []
    for r in registros:
        # FIX #6: Handle missing field - exclude if relatorAtivo is missing
        # when filtering for active relatores (conservative: undefined = not active)
        relator_ativo = r.get("relatorAtivo")
        if relator_ativo is True:
            filtrados.append(r)
        # False or None -> excluded

    return filtrados
```

**Acceptance Criteria:**
- Pure functions (no side effects)
- Return new list, don't modify original
- FIX #6: Handles missing `turmaRecursal`, `relatorAtivo` fields gracefully
- Monocratic decisions without explicit turma recursal markers are preserved
- When filtering for active relatores, records with missing `relatorAtivo` are excluded (conservative)

---

### Step 4: Update BuscaService

**MAJOR FIX #4:** Do NOT mutate the `registro` dict in-place. Use dict unpacking to create new dicts.

**MAJOR FIX #6:** Add edge case handling for monocratic decisions (missing `turmaRecursal`, `relatorAtivo` fields).

**CRITICAL FIX #2 (Reiteration):** Constructor uses `session` and `cache_manager` parameters.

**File:** `app/services/busca_service.py` (modifications)

```python
# Add imports
from app.utils.enrichment import (
    calcular_densidade,
    calcular_instancia,
    extrair_marcadores_relevancia
)
from app.utils.filtros import (  # FIX #11: Correct filename is filtros.py
    filtrar_por_instancia,
    filtrar_relatores_ativos
)
from app.schemas.decisao import DecisaoEnriquecida

# Update buscar() method
async def buscar(
    self,
    request: BuscaRequest,  # Now has excluir_turmas_recursais and apenas_ativos fields
    usuario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executa busca com enriquecimento e filtros adicionais.
    """
    try:
        # ... existing search logic ...

        # 4. Extrai dados
        dados = result.get("dados", [])
        # FIX #10: Use result.get("total") not paginacao.get("total") - _normalize_response() returns total at root level
        total = result.get("total", len(dados))
        total_antes_filtro = total  # hits.value

        # 5. Aplica filtros pós-processamento
        # FIX #3: Fields now exist in BuscaRequest schema
        excluir_tr = request.excluir_turmas_recursais or False
        apenas_ativos = request.apenas_ativos or False

        if excluir_tr or apenas_ativos:
            dados = filtrar_por_instancia(dados, excluir_tr)
            dados = filtrar_relatores_ativos(dados, apenas_ativos)

        total_depois_filtro = len(dados)

        # 6. Enriquece cada registro (FIX: use dict unpacking, no in-place mutation)
        dados_enriquecidos = []
        for registro in dados:
            # Calculate instance - handle missing fields for monocratic decisions
            instancia = calcular_instancia(
                turma_recursal=registro.get("turmaRecursal"),
                subbase=registro.get("subbase")
            )

            # Extract markers
            resumo = extrair_marcadores_relevancia(
                registro.get("marcadores")
            )

            # FIX: Use dict unpacking to create NEW dict, not mutate source
            enriched = {
                **registro,  # Copy all original fields
                "instancia": instancia,
                "resumo_relevancia": resumo,
                # Note: relatorAtivo kept as-is from original - Pydantic alias handles conversion
            }
            dados_enriquecidos.append(enriched)

        # 7. Calcula densidade
        densidade = calcular_densidade(total_antes_filtro)

        # 8. Converte para response schema using DecisaoEnriquecida
        # Pydantic aliases will map: uuid->uuid_tjdft, nomeRelator->relator, etc.
        resultados = [
            DecisaoEnriquecida(**item) for item in dados_enriquecidos
        ]

        # 9. Salva histórico
        # ... existing save logic ...

        # 10. Retorna resultados enriquecidos
        return {
            "resultados": [r.model_dump() for r in resultados],
            "total": total_antes_filtro,
            "total_filtrado": total_depois_filtro,
            "pagina": request.pagina,
            "tamanho": request.tamanho,
            "consulta_id": str(consulta.id),
            "densidade": densidade,
        }
    # ... existing error handling ...
```

**Acceptance Criteria:**
- Separates enrichment from filtering (SRP compliance)
- Returns both `total` and `total_filtrado`
- Enrichment happens after filtering
- Uses `DecisaoEnriquecida` schema (not `ConsultaDecisaoResponse`)
- FIX #4: Uses dict unpacking `{**registro, ...}` instead of in-place mutation
- FIX #6: Handles missing `turmaRecursal`, `relatorAtivo` fields gracefully via `.get()`
- FIX #3: Uses `request.excluir_turmas_recursais` and `request.apenas_ativos` directly (fields exist in schema)

---

### Step 5: Add Metadata Caching

**File:** `app/services/tjdft_client.py` (modify)

```python
# Add constants
METADATA_CACHE_TTL = 86400  # 24 hours

# Modify get_metadata() to use constant
async def get_metadata(self) -> Dict[str, Any]:
    """..."""
    cache_key = "tjdft:metadata"

    cached = self.cache.get(cache_key)
    if cached is not None:
        logger.debug("Metadata cache hit (24h TTL)")
        return json.loads(cached) if isinstance(cached, str) else cached

    # ... existing fetch logic ...

    # Use constant for TTL
    self.cache.set(cache_key, metadata, ttl=self.METADATA_CACHE_TTL)
    return metadata
```

**Acceptance Criteria:**
- Metadata cached for 24 hours
- Cache hit logged with TTL info

---

### Step 6: Create Search Endpoint

**CRITICAL FIX #1 (Reiteration):** Use `get_session()` not `get_db()` - the actual function in `app/database.py` is `get_session()`.

**CRITICAL FIX #2 (Reiteration):** Use correct `BuscaService` constructor parameters - `session` and `cache_manager`, not `db` and `cache`.

**CRITICAL FIX #3 (NEW):** Add `excluir_turmas_recursais` and `apenas_ativos` fields to `BuscaRequest` schema as optional fields with `default=None` to fix the `model_copy()` ValidationError.

**File:** `app/schemas/consulta.py` (modifications - ADD fields to BuscaRequest)

```python
# BuscaRequest - ADD these two optional fields
class BuscaRequest(BaseModel):
    """Request schema for search operations."""

    query: str = Field(..., min_length=1, description="Search query string")
    filtros: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional search filters"
    )
    pagina: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    tamanho: int = Field(
        default=20, ge=1, le=100, description="Results per page (max 100)"
    )
    # FIX #3: Add these optional fields for query parameter support
    excluir_turmas_recursais: Optional[bool] = Field(
        default=None,
        description="Exclude Juizados Especiais (turmas recursais)"
    )
    apenas_ativos: Optional[bool] = Field(
        default=None,
        description="Filter only active relatores"
    )

    model_config = {"from_attributes": True}
```

**File:** `app/api/v1/endpoints/busca.py` (new)

```python
"""Search endpoints for TJDFT decisions."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from app.schemas.consulta import BuscaRequest, BuscaResponseEnriquecida
from app.services.busca_service import BuscaService
from app.utils.cache import CacheManager
from app.database import get_session  # FIX #1: Use get_session not get_db

router = APIRouter(prefix="/busca", tags=["Busca"])


@router.post("/", response_model=BuscaResponseEnriquecida)
async def buscar_decisoes(
    request: BuscaRequest,
    # These are query parameters that override request body values
    excluir_turmas_recursais: bool = Query(
        False,
        alias="excluir_turmas_recursais",
        description="Exclude Juizados Especiais (turmas recursais)"
    ),
    apenas_ativos: bool = Query(
        False,
        alias="apenas_ativos",
        description="Filter only active relatores"
    ),
    # FIX #1: Proper dependency injection using get_session
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Busca decisões com filtros e enriquecimento.

    Features:
    - Densidade de precedentes (escasso/moderado/consolidado/massivo)
    - Segregação de instância (juizado_especial/tjdft_2a_instancia)
    - Filtro de relatores ativos
    - Marcadores de relevância

    Query Parameters:
    - excluir_turmas_recursais: Remove resultados de Juizados Especiais
    - apenas_ativos: Apenas relatores ativos no tribunal
    """
    # Use model_copy() to update the request with query param values
    request = request.model_copy(update={
        "excluir_turmas_recursais": excluir_turmas_recursais,
        "apenas_ativos": apenas_ativos
    })

    # FIX #2: Use correct parameter names: session and cache_manager
    cache = CacheManager()
    service = BuscaService(session=session, cache_manager=cache)

    return await service.buscar(request)
```

**Acceptance Criteria:**
- FIX #1: Uses `get_session` (correct function name from `app/database.py`)
- FIX #2: `BuscaService` constructor uses `session` and `cache_manager` (correct parameter names)
- FIX #3: `BuscaRequest` schema includes `excluir_turmas_recursais` and `apenas_ativos` as optional fields
- `model_copy(update={...})` now works without ValidationError (fields exist in schema)
- Query params use `alias` for URL-friendly naming (snake_case)
- Endpoint documented with features list and query parameters
- Response uses `BuscaResponseEnriquecida` schema

---

### Step 7: Register Router

**File:** `app/main.py` (modify)

```python
# Add import
from app.api.v1.endpoints.busca import router as busca_router

# Add before @app.on_event or after middleware
app.include_router(busca_router, prefix="/api/v1")
```

**Acceptance Criteria:**
- Router registered at `/api/v1/busca/`
- Appears in OpenAPI docs

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_utils/test_enrichment.py`

```python
import pytest
from app.utils.enrichment import (
    calcular_densidade,
    calcular_instancia,
    extrair_marcadores_relevancia
)

class TestCalcularDensidade:
    def test_escasso(self):
        result = calcular_densidade(10)
        assert result["categoria"] == "escasso"
        assert "Poucos precedentes" in result["alerta"]

    def test_moderado(self):
        result = calcular_densidade(100)
        assert result["categoria"] == "moderado"

    def test_consolidado(self):
        result = calcular_densidade(1000)
        assert result["categoria"] == "consolidado"

    def test_massivo(self):
        result = calcular_densidade(10000)
        assert result["categoria"] == "massivo"

class TestCalcularInstancia:
    def test_juizado_especial_turma_recursal_true(self):
        result = calcular_instancia(turma_recursal=True)
        assert result == "juizado_especial"

    def test_juizado_especial_subbase_tr(self):
        result = calcular_instancia(subbase="acordaos-tr")
        assert result == "juizado_especial"

    def test_tjdft_2a_instancia(self):
        result = calcular_instancia(turma_recursal=False, subbase="acordaos")
        assert result == "tjdft_2a_instancia"
```

**File:** `tests/test_api/test_busca.py`

```python
import pytest
from fastapi.testclient import TestClient

def test_busca_com_filtro_ativos(client: TestClient):
    response = client.post(
        "/api/v1/busca/",
        json={"query": "tributário", "pagina": 1, "tamanho": 20},
        params={"apenas_ativos": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_filtrado" in data
    assert "densidade" in data

def test_busca_excluir_turmas_recursais(client: TestClient):
    response = client.post(
        "/api/v1/busca/",
        json={"query": "", "pagina": 1, "tamanho": 20},
        params={"excluir_turmas_recursais": True}
    )
    assert response.status_code == 200
    # Verify no juizados especiais in results
```

---

## Success Criteria

1. All schema classes inherit from existing base classes (OCP compliance)
2. Enrichment logic separated from filtering logic (SRP compliance)
3. Response includes both `total` and `total_filtrado`
4. Metadata cached with 24h TTL
5. All unit tests pass
6. API documentation shows new fields and query params

---

## Rollback Plan

If issues arise:
1. Revert `app/schemas/decisao.py` to original
2. Revert `app/services/busca_service.py` to original
3. Remove new files: `app/utils/enrichment.py`, `app/api/v1/endpoints/busca.py`
4. Keep tests for future reference

---

## Open Questions

1. Should `resumo_relevancia` include full ementa or just snippets?
   - **Decision:** Just snippets from `marcadores`, full ementa only on detail endpoint

2. Should `densidade.alerta` be configurable?
   - **Decision:** Hardcoded for now, can be made configurable later

3. Should we add a detail endpoint for full decision view?
   - **Decision:** Future enhancement, not in this quick-wins scope

---

## Critic Corrections Applied (2025-03-10)

This plan was revised to address 9 corrections identified by the Critic across two verification rounds:

### CRITICAL Fixes (Blocks Execution) - Round 1

#### Fix #1: Circular Import Error (Step 2)
**Issue:** `from app.schemas.decisao import DecisaoBase` within `decisao.py` creates circular import
**Fix:** Removed the import line - `DecisaoBase` is already defined in the same file, no import needed

#### Fix #2: Missing Field Mapping (Step 2)
**Issue:** API returns `uuid`, `nomeRelator`, `descricaoOrgaoJulgador`, `dataJulgamento`, `inteiroTeorHtml` but schema expects `uuid_tjdft`, `relator`, `orgao_julgador`, `data_julgamento`, `inteiro_teor`
**Fix:** Added Pydantic `alias` parameters to `DecisaoBase` fields:
- `uuid_tjdft: str = Field(..., alias="uuid")`
- `relator: Optional[str] = Field(None, alias="nomeRelator")`
- `orgao_julgador: Optional[str] = Field(None, alias="descricaoOrgaoJulgador")`
- `data_julgamento: Optional[date] = Field(None, alias="dataJulgamento")`
- `inteiro_teor: Optional[str] = Field(None, alias="inteiroTeorHtml")`
- Plus: `processo`, `data_publicacao`, `classe` aliases

#### Fix #3: Missing Dependency Injection (Step 6)
**Issue:** Endpoint had no actual session injection, only comment placeholder
**Fix:** Provided complete working example:
```python
db: AsyncSession = Depends(get_db),
# ... later in function:
service = BuscaService(db=db, cache=cache)
return await service.buscar(request)
```

### CRITICAL Fixes (Blocks Execution) - Round 2

#### Fix #7: Wrong Dependency Function Name (Step 6)
**Issue:** Plan used `get_db()` but actual code in `app/database.py` has `get_session()`
**Fix:** Changed all `get_db` to `get_session`:
```python
# Before (WRONG):
from app.database import get_db
db: AsyncSession = Depends(get_db)

# After (CORRECT):
from app.database import get_session
session: AsyncSession = Depends(get_session)
```

#### Fix #8: Wrong Service Constructor Parameters (Steps 4, 6)
**Issue:** Plan used `BuscaService(db=db, cache=cache)` but actual constructor signature is:
```python
def __init__(self, session: AsyncSession, cache_manager: CacheManager)
```
**Fix:** Changed to correct parameter names:
```python
# Before (WRONG):
service = BuscaService(db=db, cache=cache)

# After (CORRECT):
service = BuscaService(session=session, cache_manager=cache)
```

#### Fix #9: Invalid model_copy() Fields (Step 6)
**Issue:** `model_copy(update={"excluir_turmas_recursais": ..., "apenas_ativos": ...})` raises ValidationError because these fields don't exist in `BuscaRequest` schema
**Fix:** Added these fields to `BuscaRequest` as optional with `default=None`:
```python
# Add to BuscaRequest in app/schemas/consulta.py
excluir_turmas_recursais: Optional[bool] = Field(default=None, ...)
apenas_ativos: Optional[bool] = Field(default=None, ...)
```

### MAJOR Fixes (Causes Issues) - Round 1

#### Fix #4: In-Place Mutation of Source Data (Step 4)
**Issue:** Directly modifying `registro` dict with `registro["instancia"] = ...`
**Fix:** Use dict unpacking to create new dict:
```python
enriched = {
    **registro,  # Copy all original fields
    "instancia": instancia,
    "resumo_relevancia": resumo,
}
dados_enriquecidos.append(enriched)
```

#### Fix #5: Query Parameter Handling Ambiguity (Steps 2, 6)
**Issue:** Both query params AND request body schema contained the filter fields
**Fix:** Clarified that `excluir_turmas_recursais` and `apenas_ativos` are query parameters ONLY:
- Removed from `BuscaRequest` schema (later reversed in Fix #9)
- Applied via `model_copy(update={...})` in endpoint
- Added clear documentation in endpoint docstring

#### Fix #6: Missing Edge Case Handling (Steps 3, 4)
**Issue:** `decisoes-monocraticas` lack `turmaRecursal`, `relatorAtivo` fields
**Fix:** Added guards/checks for missing fields:
- `filtrar_por_instancia`: Missing fields default to keeping the record (conservative)
- `filtrar_relatores_ativos`: Missing `relatorAtivo` excludes the record when filtering for active (conservative)
- All uses of `.get()` with appropriate defaults
- Added notes in docstrings about monocratic decision handling

### MAJOR Fixes (Causes Issues)

#### Fix #4: In-Place Mutation of Source Data (Step 4)
**Issue:** Directly modifying `registro` dict with `registro["instancia"] = ...`
**Fix:** Use dict unpacking to create new dict:
```python
enriched = {
    **registro,  # Copy all original fields
    "instancia": instancia,
    "resumo_relevancia": resumo,
}
dados_enriquecidos.append(enriched)
```

#### Fix #5: Query Parameter Handling Ambiguity (Steps 2, 6)
**Issue:** Both query params AND request body schema contained the filter fields
**Fix:** Clarified that `excluir_turmas_recursais` and `apenas_ativos` are query parameters ONLY:
- Removed from `BuscaRequest` schema
- Applied via `model_copy(update={...})` in endpoint
- Added clear documentation in endpoint docstring

#### Fix #6: Missing Edge Case Handling (Steps 3, 4)
**Issue:** `decisoes-monocraticas` lack `turmaRecursal`, `relatorAtivo` fields
**Fix:** Added guards/checks for missing fields:
- `filtrar_por_instancia`: Missing fields default to keeping the record (conservative)
- `filtrar_relatores_ativos`: Missing `relatorAtivo` excludes the record when filtering for active (conservative)
- All uses of `.get()` with appropriate defaults
- Added notes in docstrings about monocratic decision handling

### MAJOR Fixes (Causes Issues) - Round 3

#### Fix #10: Wrong Key for Total Results (Step 4)
**Issue:** Code used `paginacao.get("total")` but `_normalize_response()` returns `total` at root level, not nested under `paginacao`
**Fix:** Changed to:
```python
# Before (WRONG):
total = paginacao.get("total", len(dados))

# After (CORRECT):
total = result.get("total", len(dados))
```

#### Fix #11: Filename Inconsistency (Steps 3, 4)
**Issue:** Plan referenced `filters.py` but actual filename is `filtros.py`
**Fix:** Updated all references:
- File structure table now shows `app/utils/filtros.py` (add NEW functions)
- Step 3 header clarifies "add NEW functions to existing file"
- Step 4 import changed to `from app.utils.filtros import ...`

---

## Previous Architect Corrections (2025-03-10)

This plan was also revised to address 4 corrections identified by the Architect:

### 1. Schema Inheritance (Step 2)
**Issue:** `DecisaoResponse` in `consulta.py` wasn't inheriting from `DecisaoBase`
**Fix:** `DecisaoEnriquecida` now explicitly inherits from `DecisaoBase`, ensuring OCP compliance

### 2. Pydantic Field Aliases (Step 2)
**Issue:** Manual dict manipulation for `relatorAtivo` → `relator_ativo` conversion
**Fix:** Added Pydantic `alias="relatorAtivo"` with `model_config = {"from_attributes": True, "populate_by_name": True}`

### 3. Response Schema Correction (Step 4)
**Issue:** Code used `ConsultaDecisaoResponse` but enriched fields are in `DecisaoEnriquecida`
**Fix:** Changed to `from app.schemas.decisao import DecisaoEnriquecida` and use `DecisaoEnriquecida(**item)`

### 4. Frozen Model Handling (Step 6)
**Issue:** Direct attribute assignment fails on frozen Pydantic v2 models
**Fix:** Use `request.model_copy(update={...})` instead of `request.field = value`
