"""Schemas for consulta operations."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.decisao import DecisaoEnriquecida


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
    excluir_turmas_recursais: Optional[bool] = Field(
        None, description="Exclude turmas recursais from results"
    )
    apenas_ativos: Optional[bool] = Field(
        None, description="Filter only active relatores"
    )

    model_config = {"from_attributes": True}


class ConsultaResponse(BaseModel):
    """Response schema for consulta history."""

    id: str = Field(..., description="Consulta UUID")
    query: str = Field(..., description="Search query used")
    filtros: Optional[Dict[str, Any]] = Field(
        default=None, description="Filters applied in search"
    )
    resultados_encontrados: int = Field(..., description="Total results found")
    pagina: int = Field(..., description="Page number requested")
    tamanho: int = Field(..., description="Page size requested")
    criado_em: datetime = Field(..., description="Timestamp of consulta creation")

    model_config = {"from_attributes": True}


class DecisaoResponse(BaseModel):
    """Response schema for decision data (summary view)."""

    uuid_tjdft: str = Field(..., description="TJDFT UUID for the decision")
    processo: Optional[str] = Field(None, description="Process number")
    ementa: Optional[str] = Field(None, description="Decision summary (ementa)")
    relator: Optional[str] = Field(None, description="Relator name")
    data_julgamento: Optional[date] = Field(None, description="Judgment date")
    orgao_julgador: Optional[str] = Field(None, description="Judging body")
    classe: Optional[str] = Field(None, description="Process class/type")

    model_config = {"from_attributes": True}


class BuscaResponseEnriquecida(BaseModel):
    """Enriched response schema for search operations with density metrics."""

    resultados: List[DecisaoEnriquecida] = Field(
        ..., description="List of enriched decisions"
    )
    total: int = Field(..., description="Total results found (before filtering)")
    total_filtrado: int = Field(..., description="Total results after filtering")
    pagina: int = Field(..., description="Current page number")
    tamanho: int = Field(..., description="Results per page")
    consulta_id: str = Field(..., description="Consulta UUID for tracking")
    densidade: Optional[Dict[str, Any]] = Field(
        None, description="Density metrics by category"
    )

    model_config = {"from_attributes": True}
