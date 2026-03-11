"""Main FastAPI application entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.v1 import router as api_v1_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API do Tribunal de Justiça do Distrito Federal e Territórios",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers da API
app.include_router(api_v1_router, prefix="/api")

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "message": "TJDFT API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
