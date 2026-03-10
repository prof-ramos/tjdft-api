"""Repository for Consulta model operations."""

import uuid
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consulta import Consulta


class ConsultaRepository:
    """Repository para operações de Consulta."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def create(
        self,
        query: str,
        filtros: Optional[Dict[str, Any]],
        resultados: int,
        pagina: int = 1,
        tamanho: int = 20,
        usuario_id: Optional[uuid.UUID] = None,
    ) -> Consulta:
        """Cria nova consulta.

        Args:
            query: String de busca
            filtros: Filtros aplicados na busca
            resultados: Número de resultados encontrados
            pagina: Número da página (default: 1)
            tamanho: Tamanho da página (default: 20)
            usuario_id: ID do usuário (opcional)

        Returns:
            Consulta: Instância criada
        """
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

    async def get_by_id(self, consulta_id: uuid.UUID) -> Optional[Consulta]:
        """Busca consulta por ID.

        Args:
            consulta_id: UUID da consulta

        Returns:
            Consulta ou None se não encontrado
        """
        stmt = select(Consulta).where(Consulta.id == str(consulta_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        usuario_id: Optional[uuid.UUID] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Consulta]:
        """Lista consultas com filtros.

        Args:
            usuario_id: Filtrar por usuário
            data_inicio: Data inicial do período
            data_fim: Data final do período
            offset: Offset para paginação
            limit: Limite de resultados

        Returns:
            Lista de Consultas
        """
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if limit <= 0:
            raise ValueError("limit must be > 0")

        stmt = select(Consulta)

        conditions = []
        if usuario_id:
            conditions.append(Consulta.usuario_id == str(usuario_id))
        if data_inicio:
            conditions.append(
                Consulta.criado_em >= datetime.combine(data_inicio, time.min)
            )
        if data_fim:
            conditions.append(
                Consulta.criado_em
                < datetime.combine(data_fim + timedelta(days=1), time.min)
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(Consulta.criado_em.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, usuario_id: Optional[uuid.UUID] = None) -> int:
        """Conta total de consultas.

        Args:
            usuario_id: Filtrar por usuário (opcional)

        Returns:
            Número total de consultas
        """
        stmt = select(func.count(Consulta.id))
        if usuario_id:
            stmt = stmt.where(Consulta.usuario_id == str(usuario_id))
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def delete(self, consulta_id: uuid.UUID) -> bool:
        """Remove consulta.

        Args:
            consulta_id: UUID da consulta

        Returns:
            True se removido, False se não encontrado
        """
        stmt = delete(Consulta).where(Consulta.id == str(consulta_id))
        result = await self.session.execute(stmt)
        return bool(result.rowcount)
