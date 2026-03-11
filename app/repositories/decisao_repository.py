from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decisao import Decisao
from app.repositories.base import BaseRepository

class DecisaoRepository(BaseRepository[Decisao]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Decisao)

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
            .order_by(desc(Decisao.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_relator(self, relator: str, limit: int = 20) -> List[Decisao]:
        """Busca decisões por relator"""
        result = await self.session.execute(
            select(Decisao)
            .where(Decisao.relator.ilike(f"%{relator}%"))
            .order_by(desc(Decisao.created_at))
            .limit(limit)
        )
        return result.scalars().all()
