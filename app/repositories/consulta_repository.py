from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consulta import Consulta
from app.repositories.base import BaseRepository

class ConsultaRepository(BaseRepository[Consulta]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Consulta)

    async def get_by_query(self, query: str, skip: int = 0, limit: int = 50) -> List[Consulta]:
        """Busca consultas pelo texto da query"""
        result = await self.session.execute(
            select(Consulta)
            .where(Consulta.query.ilike(f"%{query}%"))
            .order_by(desc(Consulta.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent(self, limit: int = 10) -> List[Consulta]:
        """Retorna consultas mais recentes"""
        result = await self.session.execute(
            select(Consulta)
            .order_by(desc(Consulta.created_at))
            .limit(limit)
        )
        return result.scalars().all()
