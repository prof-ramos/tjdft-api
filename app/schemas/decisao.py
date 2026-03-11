"""Schemas for decisao operations."""

from datetime import date, datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class DecisaoBase(BaseModel):
    """Base schema for decisao with common fields."""

    uuid_tjdft: str = Field(
        ..., alias="uuid", description="TJDFT UUID for the decision"
    )
    processo: Optional[str] = Field(
        None, alias="numeroProcesso", description="Process number"
    )
    ementa: Optional[str] = Field(None, description="Decision summary (ementa)")
    inteiro_teor: Optional[str] = Field(
        None, alias="inteiroTeorHtml", description="Full decision text"
    )
    relator: Optional[str] = Field(
        None, alias="nomeRelator", description="Relator name"
    )
    data_julgamento: Optional[date] = Field(
        None, alias="dataJulgamento", description="Judgment date"
    )
    data_publicacao: Optional[date] = Field(
        None, alias="dataPublicacao", description="Publication date"
    )
    orgao_julgador: Optional[str] = Field(
        None, alias="descricaoOrgaoJulgador", description="Judging body"
    )
    classe: Optional[str] = Field(
        None, alias="descricaoClasseCnj", description="Process class/type"
    )

    @field_validator('data_julgamento', 'data_publicacao', mode='before')
    @classmethod
    def parse_datetime_to_date(cls, v):
        """Convert datetime strings to date (API externa retorna datetime)."""
        if isinstance(v, str) and 'T' in v:
            return v.split('T')[0]
        return v

    model_config = {"from_attributes": True, "populate_by_name": True}


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
    atualizado_em: Optional[datetime] = Field(None, description="Last update timestamp")


class DecisaoListResponse(BaseModel):
    """Response schema for lists of decisoes (paginated)."""

    items: list[DecisaoResponse]
    total: int = Field(..., description="Total number of items")
    pagina: int = Field(..., description="Current page number")
    tamanho: int = Field(..., description="Items per page")
    total_paginas: int = Field(..., description="Total number of pages")

    model_config = {"from_attributes": True}


class DecisaoEnriquecida(DecisaoBase):
    """Enriched decision schema with additional analysis fields."""

    resumo_relevancia: Optional[Dict[str, str]] = Field(
        None, description="Relevance summary by category"
    )
    instancia: Optional[str] = Field(None, description="Court instance (1ª/2ª)")
    relator_ativo: Optional[bool] = Field(
        None, alias="relatorAtivo", description="Whether relator is active"
    )
