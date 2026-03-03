"""SQLAlchemy models for the application."""

from app.database import Base
from app.models.consulta import Consulta
from app.models.decisao import Decisao

__all__ = ["Base", "Consulta", "Decisao"]
