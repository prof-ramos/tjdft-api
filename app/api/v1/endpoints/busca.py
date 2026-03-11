"""Search endpoints for TJDFT decisions."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.consulta import BuscaRequest, BuscaResponseEnriquecida
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

    Query Parameters:
    - excluir_turmas_recursais: Remove resultados de Juizados Especiais
    - apenas_ativos: Apenas relatores ativos no tribunal
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
