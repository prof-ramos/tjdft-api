"""Search endpoints for TJDFT decisions."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.consulta import (
    BuscaRequest,
    BuscaResponseEnriquecida,
    ConsultaResponse,
)
from app.services.busca_service import BuscaService
from app.utils.cache import get_cache

router = APIRouter(prefix="/busca", tags=["Busca"])


@router.post("/", response_model=BuscaResponseEnriquecida)
async def buscar_decisoes(
    request: BuscaRequest,
    # Query parameters that can override request body
    excluir_turmas_recursais: bool = Query(
        False,
        alias="excluir_turmas_recursais",
        description="Exclude Juizados Especiais (turmas recursais)",
    ),
    apenas_ativos: bool = Query(
        False, alias="apenas_ativos", description="Filter only active relatores"
    ),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Busca decisões com filtros e enriquecimento.

    Features:
    - Densidade de precedentes (escasso/moderado/consolidado/massivo)
    - Segregação de instância (juizado_especial/tjdft_2a_instancia)
    - Filtro de relatores ativos
    - Marcadores de relevância
    """
    # Use model_copy() to update request with query param values
    request = request.model_copy(
        update={
            "excluir_turmas_recursais": excluir_turmas_recursais,
            "apenas_ativos": apenas_ativos,
        }
    )

    cache = get_cache()
    service = BuscaService(session=session, cache_manager=cache)

    return await service.buscar(request)


@router.get("/simples", response_model=BuscaResponseEnriquecida)
async def busca_simples(
    q: str = Query(..., description="Texto da busca"),
    pagina: int = Query(0, ge=0, description="Número da página (0-indexed)"),
    limite: int = Query(20, ge=1, le=100, description="Resultados por página"),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Busca simples via GET (alias para POST /)"""
    request = BuscaRequest(query=q, pagina=pagina, tamanho=limite)
    cache = get_cache()
    service = BuscaService(session=session, cache_manager=cache)
    return await service.buscar(request)


@router.get("/filtros", response_model=BuscaResponseEnriquecida)
async def busca_com_filtros(
    q: str = Query(..., description="Texto da busca"),
    relator: Optional[str] = Query(None, description="Nome do relator"),
    classe: Optional[str] = Query(None, description="Classe processual"),
    orgao: Optional[str] = Query(None, description="Órgão julgador"),
    data_inicio: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    pagina: int = Query(0, ge=0),
    limite: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Busca avançada com filtros via GET"""
    filtros = {}
    if relator:
        filtros["relator"] = relator
    if classe:
        filtros["classe"] = classe
    if orgao:
        filtros["orgao_julgador"] = orgao
    if data_inicio:
        filtros["data_inicio"] = data_inicio
    if data_fim:
        filtros["data_fim"] = data_fim

    request = BuscaRequest(query=q, filtros=filtros, pagina=pagina, tamanho=limite)
    cache = get_cache()
    service = BuscaService(session=session, cache_manager=cache)
    return await service.buscar(request)


@router.get("/historico", response_model=List[ConsultaResponse])
async def historico_consultas(
    limite: int = Query(10, ge=1, le=50), session: AsyncSession = Depends(get_session)
) -> List[Any]:
    """Retorna histórico das últimas consultas"""
    cache = get_cache()
    service = BuscaService(session=session, cache_manager=cache)
    return await service.historico_consultas(limite=limite)
