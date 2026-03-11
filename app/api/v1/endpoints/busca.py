from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.consulta import ConsultaCreate, ConsultaResponse
from app.schemas.decisao import DecisaoResponse
from app.services.tjdft_client import TJDFTClient
from app.repositories.consulta_repository import ConsultaRepository
from app.repositories.decisao_repository import DecisaoRepository
from app.models.consulta import Consulta

router = APIRouter(prefix="/busca", tags=["Busca"])

@router.get("/", response_model=dict)
async def busca_simples(
    q: str = Query(..., description="Texto da busca"),
    pagina: int = Query(1, ge=1, description="Número da página"),
    limite: int = Query(20, ge=1, le=100, description="Resultados por página"),
    db: AsyncSession = Depends(get_db)
):
    """
    Busca simples de jurisprudência do TJDFT

    - **q**: Texto da busca
    - **pagina**: Número da página (começa em 1)
    - **limite**: Resultados por página (1-100)
    """
    try:
        async with TJDFTClient() as client:
            resultados = await client.busca_simples(
                texto=q,
                pagina=pagina,
                tamanho_pagina=limite
            )

        # Salvar consulta no histórico
        consulta_repo = ConsultaRepository(db)
        consulta = Consulta(
            query=q,
            filtros={},
            total_resultados=resultados.get("total", 0),
            pagina=pagina
        )
        await consulta_repo.create(consulta)

        return {
            "success": True,
            "query": q,
            "pagina": pagina,
            "limite": limite,
            "total": resultados.get("total", 0),
            "resultados": resultados.get("itens", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@router.get("/filtros", response_model=dict)
async def busca_com_filtros(
    q: str = Query(..., description="Texto da busca"),
    relator: Optional[str] = Query(None, description="Nome do relator"),
    classe: Optional[str] = Query(None, description="Classe processual"),
    orgao: Optional[str] = Query(None, description="Órgão julgador"),
    data_inicio: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Busca avançada com filtros

    - **q**: Texto da busca (obrigatório)
    - **relator**: Nome do relator (opcional)
    - **classe**: Classe processual (opcional)
    - **orgao**: Órgão julgador (opcional)
    - **data_inicio**: Data inicial (opcional)
    - **data_fim**: Data final (opcional)
    """
    filtros = {}
    if relator:
        filtros["relator"] = relator
    if classe:
        filtros["classe"] = classe
    if orgao:
        filtros["orgao"] = orgao
    if data_inicio:
        filtros["data_inicio"] = data_inicio
    if data_fim:
        filtros["data_fim"] = data_fim

    try:
        async with TJDFTClient() as client:
            resultados = await client.busca_com_filtros(
                texto=q,
                filtros=filtros,
                pagina=pagina,
                tamanho_pagina=limite
            )

        # Salvar consulta no histórico
        consulta_repo = ConsultaRepository(db)
        consulta = Consulta(
            query=q,
            filtros=filtros,
            total_resultados=resultados.get("total", 0),
            pagina=pagina
        )
        await consulta_repo.create(consulta)

        return {
            "success": True,
            "query": q,
            "filtros": filtros,
            "pagina": pagina,
            "limite": limite,
            "total": resultados.get("total", 0),
            "resultados": resultados.get("itens", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@router.get("/historico", response_model=List[ConsultaResponse])
async def historico_consultas(
    limite: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Retorna histórico das últimas consultas"""
    repo = ConsultaRepository(db)
    consultas = await repo.get_recent(limit=limite)
    return consultas
