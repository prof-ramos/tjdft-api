"""Consulta model for search history."""

import uuid

from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class Consulta(Base):
    """
    Model for search query history.

    Tracks user searches with filters and pagination for analytics.
    """

    __tablename__ = "consultas"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query = Column(String, nullable=False)
    filtros = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    resultados_encontrados = Column(Integer, default=0)
    pagina = Column(Integer, default=1)
    tamanho = Column(Integer, default=20)
    criado_em = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    usuario_id = Column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<Consulta(id={self.id}, query={self.query[:50]}...)>"
