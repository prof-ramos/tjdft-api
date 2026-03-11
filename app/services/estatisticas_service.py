"""Service for statistical analysis of judicial decisions."""

from collections import Counter
from datetime import date
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.decisao import Decisao
from app.repositories.consulta_repo import ConsultaRepository
from app.repositories.decisao_repo import DecisaoRepository


class EstatisticasService:
    """Serviço de análise estatística de decisões judiciais"""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
        self.decisao_repo = DecisaoRepository(session)
        self.consulta_repo = ConsultaRepository(session)

    async def analise_por_relator(
        self,
        relator: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Análise completa por relator.

        Args:
            relator: Nome do relator
            data_inicio: Data inicial do período (opcional)
            data_fim: Data final do período (opcional)

        Returns:
            Dicionário com análise completa: {
                relator: str,
                total_decisoes: int,
                orgaos: Dict[str, int],
                classes: Dict[str, int],
                temas_recorrentes: List[str],
                media_por_mes: float,
                periodo_analisado: Dict[str, date]
            }
        """
        conditions: List[ColumnElement[bool]] = [Decisao.relator.ilike(f"%{relator}%")]

        if data_inicio:
            conditions.append(Decisao.data_julgamento >= data_inicio)
        if data_fim:
            conditions.append(Decisao.data_julgamento <= data_fim)

        # Busca decisões do relator
        stmt = (
            select(Decisao)
            .where(and_(*conditions))
            .order_by(Decisao.data_julgamento.desc())
        )
        result = await self.session.execute(stmt)
        decisoes = list(result.scalars().all())

        if not decisoes:
            return {
                "relator": relator,
                "total_decisoes": 0,
                "orgaos": {},
                "classes": {},
                "temas_recorrentes": [],
                "media_por_mes": 0.0,
                "periodo_analisado": {},
            }

        # Conta por órgão
        orgaos = Counter(d.orgao_julgador for d in decisoes if d.orgao_julgador)

        # Conta por classe
        classes = Counter(d.classe for d in decisoes if d.classe)

        # Extrai temas de ementas
        ementas = [cast(str, d.ementa) for d in decisoes if d.ementa]
        temas = self._extrair_temas(ementas) if ementas else []

        # Calcula média por mês
        datas = [cast(date, d.data_julgamento) for d in decisoes if d.data_julgamento]
        media_por_mes = self._calcular_media_mensal(datas) if datas else 0.0

        # Determina período analisado
        periodo = {}
        if datas:
            periodo = {"inicio": min(datas), "fim": max(datas)}

        return {
            "relator": relator,
            "total_decisoes": len(decisoes),
            "orgaos": dict(orgaos),
            "classes": dict(classes),
            "temas_recorrentes": temas[:10],  # Top 10 temas
            "media_por_mes": round(media_por_mes, 2),
            "periodo_analisado": periodo,
        }

    async def analise_por_tema(
        self,
        tema: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Análise por tema/assunto.

        Args:
            tema: Tema para buscar nas ementas
            data_inicio: Data inicial do período (opcional)
            data_fim: Data final do período (opcional)

        Returns:
            Dicionário com análise: {
                tema: str,
                total_decisoes: int,
                relatores: Dict[str, int],
                orgaos: Dict[str, int],
                evolucao_temporal: List[Dict],
                decisoes_principais: List[Dict]
            }
        """
        conditions: List[ColumnElement[bool]] = [Decisao.ementa.ilike(f"%{tema}%")]

        if data_inicio:
            conditions.append(Decisao.data_julgamento >= data_inicio)
        if data_fim:
            conditions.append(Decisao.data_julgamento <= data_fim)

        # Busca decisões com o tema
        stmt = (
            select(Decisao)
            .where(and_(*conditions))
            .order_by(Decisao.data_julgamento.desc())
            .limit(500)
        )
        result = await self.session.execute(stmt)
        decisoes = list(result.scalars().all())

        if not decisoes:
            return {
                "tema": tema,
                "total_decisoes": 0,
                "relatores": {},
                "orgaos": {},
                "evolucao_temporal": [],
                "decisoes_principais": [],
            }

        # Conta por relator
        relatores = Counter(d.relator for d in decisoes if d.relator)

        # Conta por órgão
        orgaos = Counter(d.orgao_julgador for d in decisoes if d.orgao_julgador)

        # Evolução temporal (por mês)
        evolucao = self._agrupar_por_periodo(decisoes, "mes")

        # Decisões principais (top 5 mais recentes)
        decisoes_principais = []
        for d in decisoes[:5]:
            decisoes_principais.append(
                {
                    "uuid_tjdft": d.uuid_tjdft,
                    "processo": d.processo,
                    "ementa": (
                        d.ementa[:200] + "..."
                        if d.ementa and len(d.ementa) > 200
                        else d.ementa
                    ),
                    "relator": d.relator,
                    "data_julgamento": (
                        d.data_julgamento.isoformat() if d.data_julgamento else None
                    ),
                    "orgao_julgador": d.orgao_julgador,
                }
            )

        return {
            "tema": tema,
            "total_decisoes": len(decisoes),
            "relatores": dict(relatores.most_common(10)),
            "orgaos": dict(orgaos),
            "evolucao_temporal": evolucao,
            "decisoes_principais": decisoes_principais,
        }

    async def analise_temporal(
        self,
        data_inicio: date,
        data_fim: date,
        agrupamento: str = "mes",
    ) -> Dict[str, Any]:
        """Análise temporal de decisões.

        Args:
            data_inicio: Data inicial do período
            data_fim: Data final do período
            agrupamento: Tipo de agrupamento (dia, semana, mes, ano)

        Returns:
            Dicionário com análise temporal: {
                periodo: {inicio: date, fim: date},
                total_decisoes: int,
                serie_temporal: List[Dict],
                tendencia: str,
                pico: Dict[str, Any],
                media_por_periodo: float
            }
        """
        # Busca decisões no período
        stmt = (
            select(Decisao)
            .where(
                and_(
                    Decisao.data_julgamento >= data_inicio,
                    Decisao.data_julgamento <= data_fim,
                )
            )
            .order_by(Decisao.data_julgamento)
        )
        result = await self.session.execute(stmt)
        decisoes = list(result.scalars().all())

        if not decisoes:
            return {
                "periodo": {"inicio": data_inicio, "fim": data_fim},
                "total_decisoes": 0,
                "serie_temporal": [],
                "tendencia": "estavel",
                "pico": {},
                "media_por_periodo": 0.0,
            }

        # Agrupa por período
        serie_temporal = self._agrupar_por_periodo(decisoes, agrupamento)

        # Calcula tendência
        tendencia = self._calcular_tendencia(serie_temporal)

        # Encontra pico
        pico = {}
        if serie_temporal:
            max_item = max(serie_temporal, key=lambda x: x["count"])
            pico = {"data": max_item["data"], "count": max_item["count"]}

        # Calcula média por período
        media = (
            sum(item["count"] for item in serie_temporal) / len(serie_temporal)
            if serie_temporal
            else 0.0
        )

        return {
            "periodo": {"inicio": data_inicio, "fim": data_fim},
            "total_decisoes": len(decisoes),
            "serie_temporal": serie_temporal,
            "tendencia": tendencia,
            "pico": pico,
            "media_por_periodo": round(media, 2),
        }

    async def analise_por_orgao(
        self,
        orgao: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Análise por órgão julgador.

        Args:
            orgao: Nome do órgão julgador
            data_inicio: Data inicial do período (opcional)
            data_fim: Data final do período (opcional)

        Returns:
            Dicionário com análise: {
                orgao: str,
                total_decisoes: int,
                relatores: Dict[str, int],
                classes: Dict[str, int],
                top_relatores: List[Dict[str, Any]]
            }
        """
        conditions: List[ColumnElement[bool]] = [
            Decisao.orgao_julgador.ilike(f"%{orgao}%")
        ]

        if data_inicio:
            conditions.append(Decisao.data_julgamento >= data_inicio)
        if data_fim:
            conditions.append(Decisao.data_julgamento <= data_fim)

        # Busca decisões do órgão
        stmt = (
            select(Decisao)
            .where(and_(*conditions))
            .order_by(Decisao.data_julgamento.desc())
        )
        result = await self.session.execute(stmt)
        decisoes = list(result.scalars().all())

        if not decisoes:
            return {
                "orgao": orgao,
                "total_decisoes": 0,
                "relatores": {},
                "classes": {},
                "top_relatores": [],
            }

        # Conta por relator
        relatores = Counter(d.relator for d in decisoes if d.relator)

        # Conta por classe
        classes = Counter(d.classe for d in decisoes if d.classe)

        # Top relatores com detalhes
        top_relatores = []
        for relator, count in relatores.most_common(10):
            top_relatores.append({"relator": relator, "total": count})

        return {
            "orgao": orgao,
            "total_decisoes": len(decisoes),
            "relatores": dict(relatores),
            "classes": dict(classes),
            "top_relatores": top_relatores,
        }

    async def distribuicao_por_classe(
        self,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Distribuição de decisões por classe processual.

        Args:
            data_inicio: Data inicial do período (opcional)
            data_fim: Data final do período (opcional)

        Returns:
            Dicionário com distribuição: {
                total: int,
                classes: List[Dict],
                top_5: List[Dict],
                outras: int
            }
        """
        conditions: List[ColumnElement[bool]] = []

        if data_inicio:
            conditions.append(Decisao.data_julgamento >= data_inicio)
        if data_fim:
            conditions.append(Decisao.data_julgamento <= data_fim)

        # Conta por classe usando agregação SQL
        stmt = (
            select(Decisao.classe, func.count(Decisao.id).label("count"))
            .where(Decisao.classe.isnot(None), *conditions)
            .group_by(Decisao.classe)
            .order_by(func.count(Decisao.id).desc())
        )
        result = await self.session.execute(stmt)
        classes_count = result.all()

        if not classes_count:
            return {
                "total": 0,
                "classes": [],
                "top_5": [],
                "outras": 0,
            }

        total = sum(count for _, count in classes_count)

        # Formata lista completa com percentuais
        classes = []
        for classe, count in classes_count:
            percentual = (count / total * 100) if total > 0 else 0
            classes.append(
                {"classe": classe, "count": count, "percentual": round(percentual, 2)}
            )

        # Top 5
        top_5 = classes[:5]

        # Outras (soma do restante)
        outras = sum(item["count"] for item in classes[5:]) if len(classes) > 5 else 0

        return {
            "total": total,
            "classes": classes,
            "top_5": top_5,
            "outras": outras,
        }

    async def ranking_relatores(
        self,
        limite: int = 10,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Ranking de relatores por volume.

        Args:
            limite: Limite de resultados (default: 10)
            data_inicio: Data inicial do período (opcional)
            data_fim: Data final do período (opcional)

        Returns:
            Lista de dicionários: [
                {relator: str, total: int, orgao: str},
                ...
            ]
        """
        conditions: List[ColumnElement[bool]] = [Decisao.relator.isnot(None)]

        if data_inicio:
            conditions.append(Decisao.data_julgamento >= data_inicio)
        if data_fim:
            conditions.append(Decisao.data_julgamento <= data_fim)

        # Usa agregação SQL para performance
        stmt = (
            select(
                Decisao.relator,
                func.count(Decisao.id).label("total"),
                func.max(Decisao.orgao_julgador).label("orgao"),
            )
            .where(and_(*conditions))
            .group_by(Decisao.relator)
            .order_by(func.count(Decisao.id).desc())
            .limit(limite)
        )
        result = await self.session.execute(stmt)

        ranking = []
        for row in result:
            ranking.append(
                {"relator": row.relator, "total": row.total, "orgao": row.orgao}
            )

        return ranking

    async def comparar_periodos(
        self, periodo1: Dict[str, date], periodo2: Dict[str, date]
    ) -> Dict[str, Any]:
        """Compara dois períodos de tempo.

        Args:
            periodo1: Dicionário com 'inicio' e 'fim' (date)
            periodo2: Dicionário com 'inicio' e 'fim' (date)

        Returns:
            Dicionário com comparação: {
                periodo1: {inicio, fim, total},
                periodo2: {inicio, fim, total},
                variacao: float,
                tendencia: str,
                metricas: Dict
            }
        """
        # Conta decisões no período 1
        stmt1 = select(func.count(Decisao.id)).where(
            and_(
                Decisao.data_julgamento >= periodo1["inicio"],
                Decisao.data_julgamento <= periodo1["fim"],
            )
        )
        result1 = await self.session.execute(stmt1)
        total1 = result1.scalar_one() or 0

        # Conta decisões no período 2
        stmt2 = select(func.count(Decisao.id)).where(
            and_(
                Decisao.data_julgamento >= periodo2["inicio"],
                Decisao.data_julgamento <= periodo2["fim"],
            )
        )
        result2 = await self.session.execute(stmt2)
        total2 = result2.scalar_one() or 0

        # Calcula variação percentual
        variacao = 0.0
        if total1 > 0:
            variacao = ((total2 - total1) / total1) * 100
        elif total2 > 0:
            variacao = 100.0

        # Determina tendência
        if variacao > 5:
            tendencia = "aumento"
        elif variacao < -5:
            tendencia = "reducao"
        else:
            tendencia = "estavel"

        # Métricas adicionais
        dias1 = (periodo1["fim"] - periodo1["inicio"]).days + 1
        dias2 = (periodo2["fim"] - periodo2["inicio"]).days + 1

        media1 = total1 / dias1 if dias1 > 0 else 0
        media2 = total2 / dias2 if dias2 > 0 else 0

        return {
            "periodo1": {
                "inicio": periodo1["inicio"].isoformat(),
                "fim": periodo1["fim"].isoformat(),
                "total": total1,
            },
            "periodo2": {
                "inicio": periodo2["inicio"].isoformat(),
                "fim": periodo2["fim"].isoformat(),
                "total": total2,
            },
            "variacao": round(variacao, 2),
            "tendencia": tendencia,
            "metricas": {
                "media_por_dia_p1": round(media1, 2),
                "media_por_dia_p2": round(media2, 2),
                "variacao_media": round(
                    ((media2 - media1) / media1 * 100) if media1 > 0 else 0, 2
                ),
            },
        }

    def _agrupar_por_periodo(
        self, decisoes: List[Decisao], agrupamento: str
    ) -> List[Dict[str, Any]]:
        """Agrupa decisões por período.

        Args:
            decisoes: Lista de decisões
            agrupamento: Tipo de agrupamento (dia, semana, mes, ano)

        Returns:
            Lista de dicionários com data e count
        """
        if not decisoes:
            return []

        # Filtra apenas decisões com data de julgamento
        datas = [
            cast(date, d.data_julgamento)
            for d in decisoes
            if d.data_julgamento is not None
        ]

        if not datas:
            return []

        # Define a chave de agrupamento
        def get_periodo_key(data: date) -> str:
            if agrupamento == "dia":
                return data.isoformat()
            elif agrupamento == "semana":
                # Retorna ano-semana (YYYY-Www)
                return data.strftime("%Y-W%U")
            elif agrupamento == "mes":
                return data.strftime("%Y-%m")
            elif agrupamento == "ano":
                return data.strftime("%Y")
            else:
                return data.strftime("%Y-%m")  # Default: mês

        # Conta por período
        counter = Counter(get_periodo_key(d) for d in datas)

        # Converte para lista ordenada
        resultado = [
            {"data": periodo, "count": count}
            for periodo, count in sorted(counter.items())
        ]

        return resultado

    def _calcular_tendencia(self, serie: List[Dict]) -> str:
        """Calcula tendência da série temporal.

        Args:
            serie: Lista de dicionários com data e count

        Returns:
            String: 'crescente', 'decrescente' ou 'estavel'
        """
        if len(serie) < 2:
            return "estavel"

        # Divide série em duas metades
        mid = len(serie) // 2
        primeira_metade = serie[:mid]
        segunda_metade = serie[mid:]

        # Calcula média de cada metade
        media1 = sum(item["count"] for item in primeira_metade) / len(primeira_metade)
        media2 = sum(item["count"] for item in segunda_metade) / len(segunda_metade)

        # Determina tendência
        variacao = ((media2 - media1) / media1 * 100) if media1 > 0 else 0

        if variacao > 10:
            return "crescente"
        elif variacao < -10:
            return "decrescente"
        else:
            return "estavel"

    def _extrair_temas(self, ementas: List[str]) -> List[str]:
        """Extrai temas recorrentes de ementas.

        Args:
            ementas: Lista de textos de ementas

        Returns:
            Lista de temas mais frequentes
        """
        # Palavras-chave jurídicas comuns
        palavras_ignorar = {
            "que",
            "e",
            "de",
            "da",
            "do",
            "para",
            "com",
            "sem",
            "em",
            "por",
            "não",
            "como",
            "aos",
            "das",
            "dos",
            "se",
            "om",
            "ou",
            "un",
            "à",
            "uma",
            "sobre",
            "é",
            "foi",
        }

        # Extrai palavras com mais de 4 caracteres
        palavras = []
        for ementa in ementas:
            if not ementa:
                continue
            # Divide por espaços e pontuação
            tokens = ementa.lower().split()
            for token in tokens:
                # Remove pontuação
                token = "".join(c for c in token if c.isalnum())
                # Filtra palavras curtas e ignoradas
                if len(token) > 4 and token not in palavras_ignorar:
                    palavras.append(token)

        # Conta frequências
        counter = Counter(palavras)

        # Retorna top 20
        return [palavra for palavra, _ in counter.most_common(20)]

    def _calcular_media_mensal(self, datas: List[date]) -> float:
        """Calcula média de decisões por mês.

        Args:
            datas: Lista de datas de julgamento

        Returns:
            Média de decisões por mês
        """
        if not datas:
            return 0.0

        # Determina período em meses
        data_min = min(datas)
        data_max = max(datas)

        # Calcula diferença em meses
        meses = (
            (data_max.year - data_min.year) * 12 + (data_max.month - data_min.month) + 1
        )

        if meses <= 0:
            meses = 1

        # Calcula média
        return len(datas) / meses
