"""Repository for Decisao model operations."""

from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decisao import Decisao


class DecisaoRepository:
    """Repository para operações de Decisao."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

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
        """Cria ou atualiza decisão (upsert by uuid_tjdft).

        Args:
            uuid_tjdft: UUID do TJDFT (identificador único)
            processo: Número do processo
            ementa: Ementa da decisão
            inteiro_teor: Texto completo da decisão
            relator: Nome do relator
            data_julgamento: Data do julgamento
            data_publicacao: Data da publicação
            orgao_julgador: Órgão julgador
            classe: Classe processual

        Returns:
            Decisao: Instância criada ou atualizada
        """
        # Tenta buscar existente
        existing = await self.get_by_uuid(uuid_tjdft)

        if existing:
            # Atualiza campos
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
                setattr(existing, field, value)
            return existing
        else:
            # Cria nova
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

    async def get_by_uuid(self, uuid_tjdft: str) -> Optional[Decisao]:
        """Busca decisão por UUID do TJDFT.

        Args:
            uuid_tjdft: UUID do TJDFT

        Returns:
            Decisao ou None se não encontrado
        """
        try:
            stmt = select(Decisao).where(Decisao.uuid_tjdft == uuid_tjdft)
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except NoResultFound:
            return None

    async def get_by_relator(self, relator: str, limit: int = 100) -> List[Decisao]:
        """Busca decisões por relator.

        Args:
            relator: Nome do relator
            limit: Limite de resultados (default: 100)

        Returns:
            Lista de Decisoes
        """
        stmt = (
            select(Decisao)
            .where(Decisao.relator.ilike(f"%{relator}%"))
            .order_by(Decisao.data_julgamento.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list(
        self,
        relator: Optional[str] = None,
        orgao: Optional[str] = None,
        classe: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Decisao]:
        """Lista decisões com filtros.

        Args:
            relator: Filtrar por relator
            orgao: Filtrar por órgão julgador
            classe: Filtrar por classe
            offset: Offset para paginação
            limit: Limite de resultados

        Returns:
            Lista de Decisoes
        """
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

        stmt = stmt.order_by(Decisao.data_julgamento.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_relator(self) -> Dict[str, int]:
        """Conta decisões por relator (para estatísticas).

        Returns:
            Dicionário com relator -> quantidade
        """
        stmt = (
            select(Decisao.relator, func.count(Decisao.id))
            .where(Decisao.relator.isnot(None))
            .group_by(Decisao.relator)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def count_by_periodo(
        self, data_inicio: date, data_fim: date
    ) -> Dict[str, int]:
        """Conta decisões por mês/ano.

        Args:
            data_inicio: Data inicial do período
            data_fim: Data final do período

        Returns:
            Dicionário com formato "YYYY-MM" -> quantidade
        """
        stmt = (
            select(
                func.to_char(Decisao.data_julgamento, "YYYY-MM").label("periodo"),
                func.count(Decisao.id),
            )
            .where(
                and_(
                    Decisao.data_julgamento >= data_inicio,
                    Decisao.data_julgamento <= data_fim,
                )
            )
            .group_by("periodo")
            .order_by("periodo")
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
