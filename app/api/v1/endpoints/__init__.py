from fastapi import APIRouter
from app.api.v1.endpoints.busca import router as busca_router
from app.api.v1.endpoints.decisoes import router as decisoes_router

api_router = APIRouter()

api_router.include_router(busca_router, prefix="/busca", tags=["Busca"])
api_router.include_router(decisoes_router, prefix="/decisoes", tags=["Decisões"])
