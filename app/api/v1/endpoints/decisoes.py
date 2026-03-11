from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.decisao import DecisaoResponse
from app.repositories.decisao_repository import DecisaoRepository

router = APIRouter(prefix="/decisoes", tags=["Decisões"])

@router.get("/buscar", response_model=List[DecisaoResponse])
async def buscar_decisoes(
    texto: str = Query(..., description="Texto para buscar na ementa"),
    limite: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Busca decisões por texto na ementa"""
    repo = DecisaoRepository(db)
    decisoes = await repo.search_by_ementa(texto, limit=limite)
    return decisoes

@router.get("/relator/{relator}", response_model=List[DecisaoResponse])
async def buscar_por_relator(
    relator: str,
    limite: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Busca decisões por relator"""
    repo = DecisaoRepository(db)
    decisoes = await repo.get_by_relator(relator, limit=limite)
    return decisoes
