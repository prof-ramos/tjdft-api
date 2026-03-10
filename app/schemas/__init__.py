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
)
from app.schemas.decisao import DecisaoResponse as DecisaoFullResponse
from app.schemas.decisao import (
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
