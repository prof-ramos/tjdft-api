"""
TJDFT API fixtures for E2E testing.

Provides fixtures for interacting with the TJDFT API in tests,
including rate limiting and real client creation.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable
from typing import Any, Awaitable

import pytest

from app.services.tjdft_client import TJDFTClient
from app.utils.cache import CacheManager


async def with_rate_limit(
    func: Callable[..., Awaitable[Any]], delay: float = 0.5
) -> Any:
    """
    Execute function with rate limiting delay.

    Args:
        func: Async function to execute
        delay: Delay in seconds after execution (default: 0.5)

    Returns:
        Result of the function execution
    """
    result = await func()
    await asyncio.sleep(delay)
    return result


@pytest.fixture
def rate_limited_request() -> Callable[..., Awaitable[Any]]:
    """
    Wrapper for rate-limited requests to avoid overwhelming TJDFT API.

    Returns:
        Callable: The with_rate_limit function for rate-limited API calls
    """
    return with_rate_limit


@pytest.fixture
async def real_tjdft_client(
    e2e_cache_manager: CacheManager,
) -> AsyncGenerator[TJDFTClient, None]:
    """
    Create real TJDFT client for E2E tests.

    Uses the real TJDFT API URL when E2E_USE_REAL_TJDFT=true,
    otherwise can be configured for mock server testing.

    Yields:
        TJDFTClient instance ready for API calls
    """
    async with TJDFTClient(cache_manager=e2e_cache_manager) as client:
        yield client
