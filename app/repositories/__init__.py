"""Repositories package for database access."""

from app.repositories.consulta_repo import ConsultaRepository
from app.repositories.decisao_repo import DecisaoRepository

__all__ = ["ConsultaRepository", "DecisaoRepository"]
