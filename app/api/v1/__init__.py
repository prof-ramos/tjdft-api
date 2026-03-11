from fastapi import APIRouter
from app.api.v1.endpoints import api_router

router = APIRouter()
router.include_router(api_router, prefix="/v1")
