"""Decisao model for decision cache."""

import uuid

from sqlalchemy import Column, Date, DateTime, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Decisao(Base):
    """
    Model for cached judicial decisions.

    Stores decision data from TJDFT API to reduce external calls.
    """

    __tablename__ = "decisoes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    uuid_tjdft = Column(String, unique=True, nullable=False, index=True)
    processo = Column(String, nullable=True)
    ementa = Column(Text, nullable=True)
    inteiro_teor = Column(Text, nullable=True)
    relator = Column(String, nullable=True)
    data_julgamento = Column(Date, nullable=True)
    data_publicacao = Column(Date, nullable=True)
    orgao_julgador = Column(String, nullable=True)
    classe = Column(String, nullable=True)
    criado_em = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<Decisao(uuid_tjdft={self.uuid_tjdft}, processo={self.processo})>"
