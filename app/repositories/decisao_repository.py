"""Repository for Decisao model operations."""

import uuid
from datetime import date
from typing import Dict, List, Optional, Any

from sqlalchemy import and_, func, select, desc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decisao import Decisao
from app.repositories.base import BaseRepository


class DecisaoRepository(BaseRepository[Decisao]):
    """Repository para operações de Decisao."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        super().__init__(session, Decisao)

    async def create_or_update(
        self,
        uuid_tjdft: str,
        processo: Optional[str] = None,
        ementa: Optional[str] = None,
        inteiro_teor: Optional[str] = None,
        relator: Optional[str] = None,
        data_julgamento: Optional[date] = None,
        data_publicacao: Optional[date] = None,
        orgao_julgador: Optional[str] = None,
        classe: Optional[str] = None,
    ) -> Decisao:
        """Cria ou atualiza decisão (upsert by uuid_tjdft)."""
        existing = await self.get_by_uuid_tjdft(uuid_tjdft)

        if existing:
            updates = {
                "processo": processo,
                "ementa": ementa,
                "inteiro_teor": inteiro_teor,
                "relator": relator,
                "data_julgamento": data_julgamento,
                "data_publicacao": data_publicacao,
                "orgao_julgador": orgao_julgador,
                "classe": classe,
            }
            for field, value in updates.items():
                if value is not None:
                    setattr(existing, field, value)
            return existing
        else:
            decisao = Decisao(
                uuid_tjdft=uuid_tjdft,
                processo=processo,
                ementa=ementa,
                inteiro_teor=inteiro_teor,
                relator=relator,
                data_julgamento=data_julgamento,
                data_publicacao=data_publicacao,
                orgao_julgador=orgao_julgador,
                classe=classe,
            )
            self.session.add(decisao)
            await self.session.flush()
            return decisao

    async def get_by_uuid_tjdft(self, uuid_tjdft: str) -> Optional[Decisao]:
        """Busca decisão pelo UUID do TJDFT"""
        result = await self.session.execute(
            select(Decisao).where(Decisao.uuid_tjdft == uuid_tjdft)
        )
        return result.scalar_one_or_none()

    async def search_by_ementa(self, texto: str, limit: int = 20) -> List[Decisao]:
        """Busca decisões por texto na ementa"""
        result = await self.session.execute(
            select(Decisao)
            .where(Decisao.ementa.ilike(f"%{texto}%"))
            .order_by(desc(Decisao.criado_em))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_relator(self, relator: str, limit: int = 20) -> List[Decisao]:
        """Busca decisões por relator"""
        result = await self.session.execute(
            select(Decisao)
            .where(Decisao.relator.ilike(f"%{relator}%"))
            .order_by(desc(Decisao.criado_em))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_decisoes(
        self,
        relator: Optional[str] = None,
        orgao: Optional[str] = None,
        classe: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Decisao]:
        """Lista decisões com filtros."""
        stmt = select(Decisao)

        conditions = []
        if relator:
            conditions.append(Decisao.relator.ilike(f"%{relator}%"))
        if orgao:
            conditions.append(Decisao.orgao_julgador.ilike(f"%{orgao}%"))
        if classe:
            conditions.append(Decisao.classe.ilike(f"%{classe}%"))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(desc(Decisao.data_julgamento)).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_relator(self) -> Dict[str, int]:
        """Conta decisões por relator."""
        stmt = (
            select(Decisao.relator, func.count(Decisao.id))
            .where(Decisao.relator.isnot(None))
            .group_by(Decisao.relator)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
