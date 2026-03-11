"""
Services module for TJDFT API.

This module provides business logic services for the application.
"""

from app.services.ai_service import (
    AIService,
    AIServiceError,
    AIServiceNotAvailableError,
)
from app.services.busca_service import (
    BuscaService,
    BuscaServiceError,
    FiltroInvalidoError,
)
from app.services.estatisticas_service import EstatisticasService
from app.services.tjdft_client import (
    TJDFTAPIError,
    TJDFTClient,
    TJDFTClientError,
    TJDFTConnectionError,
    TJDFTTimeoutError,
)

__all__ = [
    # AI Service
    "AIService",
    "AIServiceError",
    "AIServiceNotAvailableError",
    # TJDFT Client
    "TJDFTClient",
    "TJDFTClientError",
    "TJDFTConnectionError",
    "TJDFTTimeoutError",
    "TJDFTAPIError",
    # Busca Service
    "BuscaService",
    "BuscaServiceError",
    "FiltroInvalidoError",
    # Estatísticas Service
    "EstatisticasService",
]
