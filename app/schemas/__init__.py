"""Pydantic schemas for the application."""

from app.schemas.analise import (
    CompararRequest,
    CompararResponse,
    ExplicarRequest,
    ExplicarResponse,
    ResumoRequest,
    ResumoResponse,
)
from app.schemas.consulta import BuscaRequest, ConsultaResponse, DecisaoResponse
from app.schemas.decisao import (
    DecisaoBase,
    DecisaoCreate,
    DecisaoListResponse,
    DecisaoResponse as DecisaoFullResponse,
    DecisaoUpdate,
)

__all__ = [
    # Consulta schemas
    "BuscaRequest",
    "ConsultaResponse",
    "DecisaoResponse",
    # Decisao schemas
    "DecisaoBase",
    "DecisaoCreate",
    "DecisaoUpdate",
    "DecisaoFullResponse",
    "DecisaoListResponse",
    # Analise schemas
    "ResumoRequest",
    "ResumoResponse",
    "CompararRequest",
    "CompararResponse",
    "ExplicarRequest",
    "ExplicarResponse",
]
