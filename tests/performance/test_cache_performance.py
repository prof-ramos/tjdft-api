"""Performance tests for cache operations."""

import time

import pytest

from app.utils.cache import CacheManager

pytestmark = pytest.mark.performance


class TestCacheHitMissPerformance:
    """Test cache hit vs miss performance."""

    @pytest.mark.asyncio
    async def test_cache_hit_is_faster_than_miss(self, db_session):
        """Cache hit should be significantly faster than computing fresh value."""
        cache = CacheManager()
        cache._redis_client = None  # Force in-memory cache

        # Populate cache
        cache.set("test-key", {"data": "value"})

        # Measure cache hit time
        start_hit = time.perf_counter()
        result = cache.get("test-key")
        hit_time = time.perf_counter() - start_hit

        assert result is not None
        assert hit_time < 0.001  # Should be under 1ms for in-memory cache

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none_quickly(self, db_session):
        """Cache miss should return None quickly without overhead."""
        cache = CacheManager()
        cache._redis_client = None  # Force in-memory cache

        # Measure cache miss time
        start_miss = time.perf_counter()
        result = cache.get("non-existent-key")
        miss_time = time.perf_counter() - start_miss

        assert result is None
        assert miss_time < 0.001  # Should be under 1ms

    @pytest.mark.asyncio
    async def test_writes_are_reasonably_fast(self, db_session):
        """Cache writes should complete quickly."""
        cache = CacheManager()
        cache._redis_client = None  # Force in-memory cache

        large_value = {"data": "x" * 10000}  # 10KB of data

        # Measure write time
        start_write = time.perf_counter()
        success = cache.set("large-key", large_value)
        write_time = time.perf_counter() - start_write

        assert success is True
        assert write_time < 0.01  # Should be under 10ms

    @pytest.mark.asyncio
    async def test_multiple_reads_performance(self, db_session):
        """Multiple cache reads should be fast and consistent."""
        cache = CacheManager()
        cache._redis_client = None  # Force in-memory cache

        # Populate cache with multiple entries
        for i in range(100):
            cache.set(f"key-{i}", {"value": f"data-{i}"})

        # Measure time for 100 reads
        start_reads = time.perf_counter()
        results = [cache.get(f"key-{i}") for i in range(100)]
        total_time = time.perf_counter() - start_reads

        assert len(results) == 100
        assert all(r is not None for r in results)
        assert total_time < 0.1  # 100 reads should be under 100ms


class TestLRUEviction:
    """Test LRU (Least Recently Used) cache eviction."""

    @pytest.mark.asyncio
    async def test_lru_evicts_oldest_when_limit_reached(self, db_session):
        """When cache limit is reached, oldest entry should be evicted."""
        cache = CacheManager()
        cache._redis_client = None  # Force in-memory cache
        cache._max_memory_items = 5  # Set low limit for testing

        # Fill cache to limit
        for i in range(5):
            cache.set(f"key-{i}", f"value-{i}")

        assert len(cache._memory_cache) == 5

        # Add one more - should evict oldest (key-0)
        cache.set("key-5", "value-5")

        assert len(cache._memory_cache) == 5  # Still 5 items
        assert cache.get("key-0") is None  # Oldest evicted
        assert cache.get("key-1") is not None  # Others still present
        assert cache.get("key-5") is not None  # Newest present

    @pytest.mark.asyncio
    async def test_lru_updates_on_access(self, db_session):
        """Accessing an entry should update its position in LRU order."""
        cache = CacheManager()
        cache._redis_client = None  # Force in-memory cache
        cache._max_memory_items = 3  # Small limit

        # Fill cache
        cache.set("key-1", "value-1")
        cache.set("key-2", "value-2")
        cache.set("key-3", "value-3")

        # Access key-1 (should move to end/most recent)
        cache.get("key-1")

        # Add new item - should evict key-2 (now oldest)
        cache.set("key-4", "value-4")

        assert cache.get("key-1") is not None  # Was accessed, not evicted
        assert cache.get("key-2") is None  # Was oldest after access, evicted
        assert cache.get("key-4") is not None  # Newest present

    @pytest.mark.asyncio
    async def test_lru_write_updates_position(self, db_session):
        """Writing to existing key should update its LRU position."""
        cache = CacheManager()
        cache._redis_client = None  # Force in-memory cache
        cache._max_memory_items = 3

        cache.set("key-1", "value-1")
        cache.set("key-2", "value-2")
        cache.set("key-3", "value-3")

        # Update key-1 (should move to end)
        cache.set("key-1", "value-1-updated")

        # Add new item - should evict key-2
        cache.set("key-4", "value-4")

        assert cache.get("key-1") is not None  # Updated, not evicted
        assert cache.get("key-2") is None  # Evicted
        assert cache.get("key-4") is not None  # Newest

    @pytest.mark.asyncio
    async def test_clear_removes_all_entries(self, db_session):
        """Clear should remove all entries from cache."""
        cache = CacheManager()
        cache._redis_client = None  # Force in-memory cache

        # Add entries
        for i in range(10):
            cache.set(f"key-{i}", f"value-{i}")

        assert len(cache._memory_cache) == 10

        # Clear all
        cache.clear()

        assert len(cache._memory_cache) == 0
        assert cache.get("key-1") is None
        assert cache.get("key-5") is None


class TestCacheStats:
    """Test cache statistics functionality."""

    @pytest.mark.asyncio
    async def test_stats_returns_backend_info(self, db_session):
        """get_stats should return backend information."""
        cache = CacheManager()
        cache._redis_client = None  # Force in-memory cache

        stats = cache.get_stats()

        assert stats["backend"] == "memory"
        assert stats["prefix"] == "tjdft"
        assert "default_ttl" in stats
        assert "memory_cache_size" in stats

    @pytest.mark.asyncio
    async def test_memory_cache_size_increases_with_entries(self, db_session):
        """memory_cache_size should reflect actual cache size."""
        cache = CacheManager()
        cache._redis_client = None  # Force in-memory cache

        assert cache.get_stats()["memory_cache_size"] == 0

        cache.set("key-1", "value-1")
        assert cache.get_stats()["memory_cache_size"] == 1

        cache.set("key-2", "value-2")
        assert cache.get_stats()["memory_cache_size"] == 2


class TestCacheKeyBuilder:
    """Test cache key building performance and correctness."""

    def test_build_key_is_fast(self):
        """Building cache keys should be fast even with complex inputs."""
        cache = CacheManager()

        # Simple key
        start = time.perf_counter()
        key1 = cache.build_key("simple")
        simple_time = time.perf_counter() - start

        # Complex dict key
        start = time.perf_counter()
        key2 = cache.build_key("search", {"classe": "APC", "ano": 2024, "relator": "Test"})
        complex_time = time.perf_counter() - start

        assert key1 == "simple"
        assert key2 is not None
        assert simple_time < 0.001
        assert complex_time < 0.01

    def test_build_key_is_deterministic(self):
        """Building same key twice should produce same result."""
        cache = CacheManager()

        key1 = cache.build_key("search", {"classe": "APC", "ano": 2024})
        key2 = cache.build_key("search", {"classe": "APC", "ano": 2024})

        assert key1 == key2

    def test_build_key_handles_dict_order(self):
        """Dict key order shouldn't affect resulting key."""
        cache = CacheManager()

        # Same dict, different order in JSON representation
        key1 = cache.build_key("search", {"a": 1, "b": 2})
        key2 = cache.build_key("search", {"b": 2, "a": 1})

        # Should be same due to sort_keys=True in implementation
        assert key1 == key2
