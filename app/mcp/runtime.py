from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import async_session_maker
from app.services.ai_service import AIService
from app.services.tjdft_client import TJDFTClient
from app.utils.cache import CacheManager


class MCPRuntime:
    """Runtime explícito para componentes usados pelo servidor MCP."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._cache: CacheManager | None = None
        self._ai_service: AIService | None = None
        self._initialized = False
        self._closed = False
        self._lifecycle_lock = asyncio.Lock()

    @property
    def cache(self) -> CacheManager:
        """Retorna a instância de cache do runtime."""
        if self._cache is None:
            self._cache = create_cache(self.settings)
        return self._cache

    @property
    def ai_service(self) -> AIService | None:
        """Retorna a instância opcional de IA já criada pelo runtime."""
        return self._ai_service

    async def initialize(self) -> None:
        """Inicializa recursos opcionais do runtime de forma idempotente."""
        async with self._lifecycle_lock:
            if self._initialized and not self._closed:
                return

            self._closed = False
            _ = self.cache
            self._ai_service = await create_ai_service(self.settings, self.cache)
            self._initialized = True

    async def close(self) -> None:
        """Encerra recursos do runtime de forma segura e idempotente."""
        async with self._lifecycle_lock:
            if self._closed:
                return

            if self._ai_service is not None:
                await self._ai_service.close()
                self._ai_service = None

            if self._cache is not None:
                self._cache.close()

            self._closed = True
            self._initialized = False

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Entrega uma ``AsyncSession`` com rollback e close garantidos."""
        async with session_scope() as session:
            yield session

    @asynccontextmanager
    async def tjdft_client(self) -> AsyncIterator[TJDFTClient]:
        """Entrega um ``TJDFTClient`` configurado a partir do runtime."""
        async with tjdft_client_context(self.settings, self.cache) as client:
            yield client

    @asynccontextmanager
    async def optional_ai_service(self) -> AsyncIterator[AIService | None]:
        """Entrega o serviço de IA inicializado, quando habilitado."""
        if self._ai_service is None and self.settings.mcp_enable_ai_tools:
            await self.initialize()
        yield self._ai_service


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Context manager para sessão assíncrona baseada em ``async_session_maker``."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def create_cache(settings: Settings | None = None) -> CacheManager:
    """Cria um ``CacheManager`` a partir das configurações da aplicação."""
    resolved_settings = settings or get_settings()
    return CacheManager(
        redis_url=resolved_settings.redis_url,
        default_ttl=resolved_settings.cache_ttl,
        prefix="tjdft",
    )


@asynccontextmanager
async def tjdft_client_context(
    settings: Settings | None = None,
    cache: CacheManager | None = None,
) -> AsyncIterator[TJDFTClient]:
    """Cria um contexto seguro para uso de ``TJDFTClient``."""
    resolved_settings = settings or get_settings()
    resolved_cache = cache or create_cache(resolved_settings)
    async with TJDFTClient(
        resolved_cache,
        timeout=resolved_settings.mcp_request_timeout_seconds,
    ) as client:
        yield client


async def create_ai_service(
    settings: Settings | None = None,
    cache: CacheManager | None = None,
) -> AIService | None:
    """Cria e inicializa opcionalmente um ``AIService``."""
    resolved_settings = settings or get_settings()
    if not resolved_settings.mcp_enable_ai_tools:
        return None

    resolved_cache = cache or create_cache(resolved_settings)
    service = AIService(resolved_settings, resolved_cache)
    await service.initialize()
    return service


@asynccontextmanager
async def ai_service_context(
    settings: Settings | None = None,
    cache: CacheManager | None = None,
) -> AsyncIterator[AIService | None]:
    """Cria um contexto para ``AIService`` com initialize/close garantidos."""
    service = await create_ai_service(settings=settings, cache=cache)
    try:
        yield service
    finally:
        if service is not None:
            await service.close()


def create_runtime(settings: Settings | None = None) -> MCPRuntime:
    """Factory explícita para o runtime MCP."""
    return MCPRuntime(settings=settings)
