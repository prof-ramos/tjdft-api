"""Schemas for consulta operations."""

import uuid
from datetime import datetime, date
from typing import Optional, Any, Dict

from pydantic import BaseModel, Field


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
