"""Serviço unificado de busca de decisões judiciais."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.consulta_repo import ConsultaRepository
from app.repositories.decisao_repo import DecisaoRepository
from app.schemas.consulta import BuscaRequest
from app.schemas.consulta import DecisaoResponse as ConsultaDecisaoResponse
from app.schemas.decisao import DecisaoEnriquecida
from app.services.tjdft_client import TJDFTClient
from app.utils.cache import CacheManager
from app.utils.enrichment import (
    calcular_densidade,
    calcular_instancia,
    extrair_marcadores_relevancia,
)
from app.utils.filtros import (
    filtrar_por_instancia,
    filtrar_relatores_ativos,
    validate_classe,
    validate_orgao,
    validate_relator,
)

logger = logging.getLogger(__name__)


class BuscaServiceError(Exception):
    """Base exception for BuscaService errors."""

    pass


class FiltroInvalidoError(BuscaServiceError):
    """Exception raised when filter validation fails."""

    pass


class BuscaService:
    """
    Serviço unificado de busca de decisões judiciais.

    Este serviço coordena a busca na API do TJDFT, validação de filtros,
    salvamento de histórico e cache de decisões.
    """

    def __init__(
        self,
        session: AsyncSession,
        cache_manager: CacheManager,
    ):
        """
        Inicializa o serviço de busca.

        Args:
            session: Sessão assíncrona do banco de dados
            cache_manager: Gerenciador de cache
        """
        self.session = session
        self.cache = cache_manager
        self.consulta_repo = ConsultaRepository(session)
        self.decisao_repo = DecisaoRepository(session)
        logger.info("BuscaService initialized")

    async def buscar(
        self,
        request: BuscaRequest,
        usuario_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executa busca e salva histórico.

        Args:
            request: Objeto BuscaRequest com query, filtros e paginação
            usuario_id: ID do usuário (opcional)

        Returns:
            Dict com:
                - resultados: List[DecisaoResponse]
                - total: int
                - pagina: int
                - tamanho: int
                - consulta_id: str

        Raises:
            FiltroInvalidoError: Se filtros forem inválidos
            BuscaServiceError: Se houver erro na busca
        """
        try:
            logger.info(
                f"Starting search: query='{request.query}', "
                f"pagina={request.pagina}, tamanho={request.tamanho}"
            )

            # 1. Valida filtros se fornecidos
            filtros = request.filtros or {}
            if filtros:
                await self._validar_filtros(filtros)
                logger.debug(f"Filters validated: {filtros}")

            # 2. Prepara parâmetros para API
            kwargs = self._prepare_api_params(filtros)

            # 3. Busca na API do TJDFT
            async with TJDFTClient(self.cache) as client:
                if kwargs:
                    result = await client.buscar_com_filtros(
                        query=request.query,
                        pagina=request.pagina,
                        tamanho=request.tamanho,
                        **kwargs,
                    )
                else:
                    result = await client.buscar_simples(
                        query=request.query,
                        pagina=request.pagina,
                        tamanho=request.tamanho,
                    )

            # 4. Extrai dados
            dados = result.get("dados") or result.get("registros", [])
            total_antes_filtro = result.get("total", len(dados))

            logger.info(
                "Search completed: %s results found (total=%s)",
                len(dados),
                total_antes_filtro,
            )

            # 5. Apply filters if requested
            excluir_tr = request.excluir_turmas_recursais or False
            apenas_ativos = request.apenas_ativos or False

            if excluir_tr or apenas_ativos:
                dados = filtrar_por_instancia(dados, excluir_tr)
                dados = filtrar_relatores_ativos(dados, apenas_ativos)

            total_depois_filtro = len(dados)

            # 6. Enrich data with instancia and relevance summary
            # Using list comprehension since enrichment functions are synchronous
            dados_enriquecidos = [
                {
                    **registro,
                    "instancia": calcular_instancia(
                        turma_recursal=registro.get("turmaRecursal"),
                        subbase=registro.get("subbase"),
                    ),
                    "resumo_relevancia": extrair_marcadores_relevancia(
                        registro.get("marcadores")
                    ),
                }
                for registro in dados
            ]

            # 7. Calculate density metrics
            densidade = calcular_densidade(total_antes_filtro)

            # 8. Converte para response schemas enriquecidos
            resultados = [DecisaoEnriquecida(**item) for item in dados_enriquecidos]

            # 9. Salva histórico
            consulta = await self.consulta_repo.create(
                query=request.query,
                filtros=filtros,
                resultados=total_antes_filtro,
                pagina=request.pagina,
                tamanho=request.tamanho,
                usuario_id=uuid.UUID(usuario_id) if usuario_id else None,
            )
            logger.debug(f"Consulta saved: {consulta.id}")

            # 10. Salva decisões em cache (background)
            if dados:
                await self._salvar_decisoes_cache(dados)

            # 11. Retorna resultados enriquecidos
            return {
                "resultados": [r.model_dump() for r in resultados],
                "total": total_antes_filtro,
                "total_filtrado": total_depois_filtro,
                "pagina": request.pagina,
                "tamanho": request.tamanho,
                "consulta_id": str(consulta.id),
                "densidade": densidade,
            }

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise FiltroInvalidoError(str(e)) from e
        except Exception as e:
            logger.error(f"Error during search: {e}", exc_info=True)
            raise BuscaServiceError(f"Erro ao realizar busca: {e}") from e

    async def buscar_com_filtro_avancado(
        self,
        query: str,
        relator: Optional[str] = None,
        classe: Optional[str] = None,
        orgao_julgador: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        pagina: int = 1,
        tamanho: int = 20,
        usuario_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Busca com filtros avançados.

        Args:
            query: Termo de busca
            relator: Nome do relator
            classe: Classe processual
            orgao_julgador: Órgão julgador
            data_inicio: Data início (formato ISO)
            data_fim: Data fim (formato ISO)
            pagina: Número da página
            tamanho: Tamanho da página
            usuario_id: ID do usuário

        Returns:
            Dict com resultados paginados
        """
        filtros = self._build_filtros_dict(
            relator=relator,
            classe=classe,
            orgao_julgador=orgao_julgador,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        request = BuscaRequest(
            query=query,
            filtros=filtros if any(filtros.values()) else None,
            pagina=pagina,
            tamanho=tamanho,
        )

        return await self.buscar(request, usuario_id)

    async def recuperar_busca(
        self,
        consulta_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera busca salva pelo ID.

        Args:
            consulta_id: UUID da consulta

        Returns:
            Dict com dados da consulta ou None se não encontrada
        """
        try:
            consulta_uuid = uuid.UUID(consulta_id)
            consulta = await self.consulta_repo.get_by_id(consulta_uuid)

            if not consulta:
                logger.warning(f"Consulta not found: {consulta_id}")
                return None

            logger.info(f"Consulta retrieved: {consulta_id}")

            return {
                "id": str(consulta.id),
                "query": consulta.query,
                "filtros": consulta.filtros,
                "resultados_encontrados": consulta.resultados_encontrados,
                "pagina": consulta.pagina,
                "tamanho": consulta.tamanho,
                "criado_em": consulta.criado_em.isoformat(),
                "usuario_id": consulta.usuario_id,
            }

        except ValueError:
            logger.error(f"Invalid UUID format: {consulta_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving consulta: {e}", exc_info=True)
            return None

    async def buscar_todas_paginas(
        self,
        query: str,
        max_paginas: int = 5,
        usuario_id: Optional[str] = None,
        **filtros,
    ) -> Dict[str, Any]:
        """
        Busca todas as páginas e retorna agregado.

        Args:
            query: Termo de busca
            max_paginas: Número máximo de páginas
            usuario_id: ID do usuário
            **filtros: Filtros adicionais

        Returns:
            Dict com todos os resultados agregados
        """
        try:
            logger.info(
                f"Starting multi-page search: query='{query}', max_pages={max_paginas}"
            )

            async with TJDFTClient(self.cache) as client:
                all_results = await client.buscar_todas_paginas(
                    query=query,
                    max_paginas=max_paginas,
                    tamanho=20,
                    **filtros,
                )

            logger.info(
                f"Multi-page search completed: {len(all_results)} total results"
            )

            # Converte para response schemas
            resultados = [
                ConsultaDecisaoResponse(**item) for item in all_results if item
            ]

            # Salva primeira página como histórico
            if filtros:
                filtros_dict = self._build_filtros_dict(**filtros)
            else:
                filtros_dict = {}

            await self.consulta_repo.create(
                query=query,
                filtros=filtros_dict if filtros_dict else None,
                resultados=len(resultados),
                pagina=1,
                tamanho=max_paginas * 20,  # Tamanho agregado
                usuario_id=uuid.UUID(usuario_id) if usuario_id else None,
            )

            # Salva decisões em cache
            if all_results:
                await self._salvar_decisoes_cache(all_results)

            return {
                "resultados": [r.model_dump() for r in resultados],
                "total": len(resultados),
                "pagina": 1,
                "tamanho": len(resultados),
                "paginas_busca": max_paginas,
            }

        except Exception as e:
            logger.error(f"Error in multi-page search: {e}", exc_info=True)
            raise BuscaServiceError(f"Erro ao buscar todas as páginas: {e}") from e

    async def buscar_similares(
        self,
        uuid_tjdft: str,
        limite: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Busca decisões similares baseado em filtros da decisão.

        Args:
            uuid_tjdft: UUID da decisão de referência
            limite: Limite de resultados

        Returns:
            Lista de decisões similares
        """
        try:
            logger.info(f"Searching similar decisions for: {uuid_tjdft}")

            # Busca decisão no cache
            decisao = await self.decisao_repo.get_by_uuid(uuid_tjdft)

            if not decisao:
                logger.warning(f"Decision not found in cache: {uuid_tjdft}")
                return []

            # Monta filtros baseados na decisão
            filtros: Dict[str, str] = {}
            if decisao.relator is not None:
                filtros["relator"] = str(decisao.relator)
            if decisao.classe is not None:
                filtros["classe"] = str(decisao.classe)
            if decisao.orgao_julgador is not None:
                filtros["orgao_julgador"] = str(decisao.orgao_julgador)

            # Se não tem filtros suficientes, retorna vazio
            if not filtros:
                logger.info("No filters available for similar search")
                return []

            # Busca no repositório
            decisoes = await self.decisao_repo.list(
                relator=filtros.get("relator"),
                orgao=filtros.get("orgao_julgador"),
                classe=filtros.get("classe"),
                limit=limite + 1,  # +1 para excluir a própria
            )

            # Remove a decisão de referência
            similares = [d for d in decisoes if d.uuid_tjdft != uuid_tjdft][:limite]

            logger.info(f"Found {len(similares)} similar decisions")

            # Converte para dict
            return [
                {
                    "uuid_tjdft": d.uuid_tjdft,
                    "processo": d.processo,
                    "ementa": d.ementa,
                    "relator": d.relator,
                    "data_julgamento": (
                        d.data_julgamento.isoformat() if d.data_julgamento else None
                    ),
                    "orgao_julgador": d.orgao_julgador,
                    "classe": d.classe,
                }
                for d in similares
            ]

        except Exception as e:
            logger.error(f"Error searching similar decisions: {e}", exc_info=True)
            raise BuscaServiceError(f"Erro ao buscar decisões similares: {e}") from e

    async def historico_consultas(
        self,
        usuario_id: Optional[str] = None,
        limite: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Retorna histórico de consultas do usuário.

        Args:
            usuario_id: ID do usuário (opcional)
            limite: Limite de resultados

        Returns:
            Lista de consultas
        """
        try:
            logger.info(
                f"Retrieving consulta history: usuario_id={usuario_id}, limit={limite}"
            )

            usuario_uuid = uuid.UUID(usuario_id) if usuario_id else None
            consultas = await self.consulta_repo.list(
                usuario_id=usuario_uuid,
                offset=0,
                limit=limite,
            )

            logger.info(f"Found {len(consultas)} consultas")

            return [
                {
                    "id": str(c.id),
                    "query": c.query,
                    "filtros": c.filtros,
                    "resultados_encontrados": c.resultados_encontrados,
                    "pagina": c.pagina,
                    "tamanho": c.tamanho,
                    "criado_em": c.criado_em.isoformat(),
                    "usuario_id": c.usuario_id,
                }
                for c in consultas
            ]

        except ValueError:
            logger.error(f"Invalid usuario_id format: {usuario_id}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving consulta history: {e}", exc_info=True)
            raise BuscaServiceError(f"Erro ao recuperar histórico: {e}") from e

    async def _salvar_decisoes_cache(
        self,
        decisoes: List[Dict[str, Any]],
    ) -> None:
        """
        Salva decisões em cache (background).

        Args:
            decisoes: Lista de decisões da API
        """
        try:
            logger.debug(f"Caching {len(decisoes)} decisions")

            for item in decisoes:
                try:
                    # Extrai dados
                    uuid_tjdft = item.get("uuid_tjdft")
                    if not uuid_tjdft:
                        continue

                    # Parse datas se existirem
                    data_julgamento = None
                    data_publicacao = None

                    if item.get("data_julgamento"):
                        try:
                            data_julgamento = datetime.fromisoformat(
                                item["data_julgamento"]
                            ).date()
                        except (ValueError, TypeError):
                            pass

                    if item.get("data_publicacao"):
                        try:
                            data_publicacao = datetime.fromisoformat(
                                item["data_publicacao"]
                            ).date()
                        except (ValueError, TypeError):
                            pass

                    # Salva usando upsert
                    await self.decisao_repo.create_or_update(
                        uuid_tjdft=uuid_tjdft,
                        processo=item.get("processo"),
                        ementa=item.get("ementa"),
                        inteiro_teor=item.get("inteiro_teor"),
                        relator=item.get("relator"),
                        data_julgamento=data_julgamento,
                        data_publicacao=data_publicacao,
                        orgao_julgador=item.get("orgao_julgador"),
                        classe=item.get("classe"),
                    )

                except Exception as e:
                    logger.warning(
                        f"Error caching decision {item.get('uuid_tjdft')}: {e}"
                    )
                    continue

            logger.debug("Decisions cached successfully")

        except Exception as e:
            logger.error(f"Error in _salvar_decisoes_cache: {e}", exc_info=True)

    async def _validar_filtros(
        self,
        filtros: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Valida filtros contra dados de referência.

        Args:
            filtros: Dicionário de filtros

        Returns:
            Filtros validados

        Raises:
            FiltroInvalidoError: Se algum filtro for inválido
        """
        erros = []

        # Valida relator
        if "relator" in filtros and filtros["relator"]:
            if not validate_relator(filtros["relator"]):
                erros.append(f"Relator inválido: {filtros['relator']}")

        # Valida classe
        if "classe" in filtros and filtros["classe"]:
            if not validate_classe(filtros["classe"]):
                erros.append(f"Classe inválida: {filtros['classe']}")

        # Valida orgao_julgador
        if "orgao_julgador" in filtros and filtros["orgao_julgador"]:
            if not validate_orgao(filtros["orgao_julgador"]):
                erros.append(f"Órgão julgador inválido: {filtros['orgao_julgador']}")

        if erros:
            erro_msg = "; ".join(erros)
            logger.error(f"Filter validation errors: {erro_msg}")
            raise FiltroInvalidoError(erro_msg)

        return filtros

    def _build_filtros_dict(
        self,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Constrói dicionário de filtros removendo valores None.

        Args:
            **kwargs: Argumentos nomeados dos filtros

        Returns:
            Dicionário de filtros limpo
        """
        return {
            key: value
            for key, value in kwargs.items()
            if value is not None and value != ""
        }

    def _prepare_api_params(
        self,
        filtros: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Prepara parâmetros para chamada da API.

        Args:
            filtros: Dicionário de filtros

        Returns:
            Dicionário de parâmetros para API
        """
        # Mapeamento de nomes de filtros para parâmetros da API
        api_params = {}

        filtro_mapping = {
            "relator": "relator",
            "classe": "classe",
            "orgao_julgador": "orgao_julgador",
            "data_inicio": "data_inicio",
            "data_fim": "data_fim",
        }

        for filtro_nome, api_nome in filtro_mapping.items():
            if filtro_nome in filtros and filtros[filtro_nome]:
                api_params[api_nome] = filtros[filtro_nome]

        return api_params

    async def _paginar_resultados(
        self,
        todos_resultados: List,
        pagina: int,
        tamanho: int,
    ) -> Dict[str, Any]:
        """
        Pagina lista de resultados client-side.

        Args:
            todos_resultados: Lista completa de resultados
            pagina: Número da página (1-indexed)
            tamanho: Tamanho da página

        Returns:
            Dict com resultados paginados
        """
        total = len(todos_resultados)
        total_paginas = (total + tamanho - 1) // tamanho if tamanho > 0 else 1

        # Calcula índices
        inicio = (pagina - 1) * tamanho
        fim = inicio + tamanho

        # Extrai página
        resultados_pagina = todos_resultados[inicio:fim]

        return {
            "resultados": resultados_pagina,
            "total": total,
            "pagina": pagina,
            "tamanho": tamanho,
            "total_paginas": total_paginas,
        }
