"""Schemas for decisao operations."""

import uuid
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


class DecisaoBase(BaseModel):
    """Base schema for decisao with common fields."""

    uuid_tjdft: str = Field(..., description="TJDFT UUID for the decision")
    processo: Optional[str] = Field(None, description="Process number")
    ementa: Optional[str] = Field(None, description="Decision summary (ementa)")
    inteiro_teor: Optional[str] = Field(None, description="Full decision text")
    relator: Optional[str] = Field(None, description="Relator name")
    data_julgamento: Optional[date] = Field(None, description="Judgment date")
    data_publicacao: Optional[date] = Field(None, description="Publication date")
    orgao_julgador: Optional[str] = Field(None, description="Judging body")
    classe: Optional[str] = Field(None, description="Process class/type")

    model_config = {"from_attributes": True}


class DecisaoCreate(DecisaoBase):
    """Schema for creating a new decisao."""

    pass


class DecisaoUpdate(BaseModel):
    """Schema for updating a decisao (all fields optional)."""

    processo: Optional[str] = None
    ementa: Optional[str] = None
    inteiro_teor: Optional[str] = None
    relator: Optional[str] = None
    data_julgamento: Optional[date] = None
    data_publicacao: Optional[date] = None
    orgao_julgador: Optional[str] = None
    classe: Optional[str] = None

    model_config = {"from_attributes": True}


class DecisaoResponse(DecisaoBase):
    """Complete response schema for decisao."""

    id: str = Field(..., description="Internal database ID")
    criado_em: datetime = Field(..., description="Creation timestamp")
    atualizado_em: Optional[datetime] = Field(
        None, description="Last update timestamp"
    )


class DecisaoListResponse(BaseModel):
    """Response schema for lists of decisoes (paginated)."""

    items: list[DecisaoResponse]
    total: int = Field(..., description="Total number of items")
    pagina: int = Field(..., description="Current page number")
    tamanho: int = Field(..., description="Items per page")
    total_paginas: int = Field(..., description="Total number of pages")

    model_config = {"from_attributes": True}
