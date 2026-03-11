"""Repository for Consulta model operations."""

import uuid
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consulta import Consulta
from app.repositories.base import BaseRepository


class ConsultaRepository(BaseRepository[Consulta]):
    """Repository para operações de Consulta."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        super().__init__(session, Consulta)

    async def create_query(
        self,
        query: str,
        filtros: Optional[Dict[str, Any]],
        resultados: int,
        pagina: int = 1,
        tamanho: int = 20,
        usuario_id: Optional[uuid.UUID] = None,
    ) -> Consulta:
        """Cria nova consulta."""
        consulta = Consulta(
            query=query,
            filtros=filtros,
            resultados_encontrados=resultados,
            pagina=pagina,
            tamanho=tamanho,
            usuario_id=str(usuario_id) if usuario_id else None,
        )
        self.session.add(consulta)
        await self.session.flush()
        return consulta

    async def get_by_id(self, id: Any) -> Optional[Consulta]:
        """Busca consulta por ID."""
        return await self.get(id)

    async def get_by_query(self, query: str, skip: int = 0, limit: int = 50) -> List[Consulta]:
        """Busca consultas pelo texto da query"""
        result = await self.session.execute(
            select(Consulta)
            .where(Consulta.query.ilike(f"%{query}%"))
            .order_by(desc(Consulta.criado_em))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 10) -> List[Consulta]:
        """Retorna consultas mais recentes"""
        result = await self.session.execute(
            select(Consulta)
            .order_by(desc(Consulta.criado_em))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_consultas(
        self,
        usuario_id: Optional[uuid.UUID] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Consulta]:
        """Lista consultas com filtros."""
        stmt = select(Consulta)

        conditions = []
        if usuario_id:
            conditions.append(Consulta.usuario_id == str(usuario_id))
        
        if data_inicio:
            conditions.append(Consulta.criado_em >= datetime.combine(data_inicio, time.min))
        if data_fim:
            conditions.append(Consulta.criado_em < datetime.combine(data_fim + timedelta(days=1), time.min))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(desc(Consulta.criado_em)).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_consultas(self, usuario_id: Optional[uuid.UUID] = None) -> int:
        """Conta total de consultas."""
        stmt = select(func.count(Consulta.id))
        if usuario_id:
            stmt = stmt.where(Consulta.usuario_id == str(usuario_id))
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
