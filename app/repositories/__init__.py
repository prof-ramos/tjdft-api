"""Repositories package for database access."""

from app.repositories.base import BaseRepository
from app.repositories.consulta_repository import ConsultaRepository
from app.repositories.decisao_repository import DecisaoRepository

__all__ = ["BaseRepository", "ConsultaRepository", "DecisaoRepository"]
