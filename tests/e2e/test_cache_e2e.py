"""
E2E tests for cache integration with real Redis.

Tests verify that caching works correctly with the Redis container
and that cache hits return consistent data.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_manager_connects_to_redis(e2e_cache_manager):
    """Test that CacheManager successfully connects to Redis container."""
    stats = e2e_cache_manager.get_stats()
    assert stats["backend"] == "redis"
    assert "redis_version" in stats or stats["backend"] == "memory"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_set_and_get(e2e_cache_manager):
    """Test basic cache set and get operations."""
    # Arrange
    test_key = "test:e2e:key"
    test_value = {"data": "test", "number": 123}

    # Act - Set
    set_result = e2e_cache_manager.set(test_key, test_value, ttl=60)
    assert set_result is True

    # Act - Get
    retrieved = e2e_cache_manager.get(test_key)

    # Assert
    assert retrieved is not None
    assert retrieved["data"] == "test"
    assert retrieved["number"] == 123

    # Cleanup
    e2e_cache_manager.delete(test_key)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_miss_returns_none(e2e_cache_manager):
    """Test that cache miss returns None."""
    result = e2e_cache_manager.get("nonexistent:key:xyz")
    assert result is None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_exists_check(e2e_cache_manager):
    """Test cache exists method."""
    test_key = "test:e2e:exists"

    # Before set
    assert e2e_cache_manager.exists(test_key) is False

    # After set
    e2e_cache_manager.set(test_key, {"exists": True}, ttl=60)
    assert e2e_cache_manager.exists(test_key) is True

    # After delete
    e2e_cache_manager.delete(test_key)
    assert e2e_cache_manager.exists(test_key) is False


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_clear(e2e_cache_manager):
    """Test clearing all cache entries with prefix."""
    # Set multiple keys
    e2e_cache_manager.set("test:clear:1", {"data": 1}, ttl=60)
    e2e_cache_manager.set("test:clear:2", {"data": 2}, ttl=60)
    e2e_cache_manager.set("test:clear:3", {"data": 3}, ttl=60)

    # Verify they exist
    assert e2e_cache_manager.exists("test:clear:1")
    assert e2e_cache_manager.exists("test:clear:2")

    # Clear
    clear_result = e2e_cache_manager.clear()
    assert clear_result is True

    # Verify cleared
    assert e2e_cache_manager.exists("test:clear:1") is False
    assert e2e_cache_manager.exists("test:clear:2") is False


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_hit_returns_same_data(real_tjdft_client, e2e_cache_manager):
    """Test that cache returns same data on second call."""
    # First call - cache miss
    result1 = await real_tjdft_client.buscar_simples("tributário", pagina=0, tamanho=5)

    # Second call - cache hit
    result2 = await real_tjdft_client.buscar_simples("tributário", pagina=0, tamanho=5)

    # Assert same data
    assert result1["total"] == result2["total"]
    assert len(result1["registros"]) == len(result2["registros"])


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_key_isolation(e2e_cache_manager):
    """Test that different queries create different cache keys."""
    key1 = e2e_cache_manager.build_key("search", {"query": "test1"})
    key2 = e2e_cache_manager.build_key("search", {"query": "test2"})

    assert key1 != key2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_ttl_expiration(e2e_cache_manager):
    """Test cache entry respects TTL (time-to-live)."""
    import asyncio

    test_key = "test:e2e:ttl"
    test_value = {"expires": "soon"}

    # Set with very short TTL
    e2e_cache_manager.set(test_key, test_value, ttl=1)

    # Immediately get - should exist
    immediate = e2e_cache_manager.get(test_key)
    assert immediate is not None

    # Wait for expiration
    await asyncio.sleep(1.5)

    # After TTL - should be gone
    expired = e2e_cache_manager.get(test_key)
    assert expired is None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_json_serialization(e2e_cache_manager):
    """Test that complex JSON structures are properly serialized."""
    complex_data = {
        "string": "value",
        "number": 42,
        "float": 3.14,
        "bool": True,
        "null": None,
        "list": [1, 2, 3],
        "nested": {"key": "value"},
        "registros": [
            {"id": 1, "nome": "Test 1"},
            {"id": 2, "nome": "Test 2"},
        ],
    }

    e2e_cache_manager.set("test:complex", complex_data, ttl=60)
    retrieved = e2e_cache_manager.get("test:complex")

    assert retrieved == complex_data
    assert retrieved["nested"]["key"] == "value"
    assert len(retrieved["registros"]) == 2

    # Cleanup
    e2e_cache_manager.delete("test:complex")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_delete_nonexistent_key(e2e_cache_manager):
    """Test that deleting non-existent key returns True (idempotent)."""
    result = e2e_cache_manager.delete("does:not:exist:key")
    assert result is True
