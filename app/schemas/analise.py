"""Schemas for AI analysis operations."""

from typing import List

from pydantic import BaseModel, Field


class ResumoRequest(BaseModel):
    """Request schema for generating decision summaries."""

    ementa: str = Field(
        ..., min_length=1, description="Decision ementa text to summarize"
    )

    model_config = {"from_attributes": True}


class ResumoResponse(BaseModel):
    """Response schema for decision summaries."""

    resumo: str = Field(..., description="Generated summary text")
    pontos_chave: List[str] = Field(
        default_factory=list, description="Key points extracted from the decision"
    )

    model_config = {"from_attributes": True}


class CompararRequest(BaseModel):
    """Request schema for comparing multiple decisions."""

    decisoes: List[str] = Field(
        ...,
        min_length=2,
        max_length=10,
        description="List of ementas to compare (2-10 items)",
    )

    model_config = {"from_attributes": True}


class CompararResponse(BaseModel):
    """Response schema for decision comparison results."""

    similaridades: List[str] = Field(
        default_factory=list, description="Similarities found between decisions"
    )
    diferencas: List[str] = Field(
        default_factory=list, description="Differences found between decisions"
    )
    analise: str = Field(..., description="Overall comparison analysis")

    model_config = {"from_attributes": True}


class ExplicarRequest(BaseModel):
    """Request schema for explaining legal concepts."""

    termo: str = Field(
        ..., min_length=1, description="Legal term or concept to explain"
    )
    contexto: str = Field(
        default="",
        description="Optional context for better explanation",
    )

    model_config = {"from_attributes": True}


class ExplicarResponse(BaseModel):
    """Response schema for legal concept explanations."""

    termo: str = Field(..., description="The term that was explained")
    explicacao: str = Field(..., description="Explanation of the term")
    exemplos: List[str] = Field(default_factory=list, description="Practical examples")
    termos_relacionados: List[str] = Field(
        default_factory=list, description="Related legal terms"
    )

    model_config = {"from_attributes": True}
