import time
from unittest.mock import MagicMock

import pytest

import app.utils.cache as cache_module
from app.utils.cache import CacheManager, get_cache

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_global_cache_instance():
    cache_module._cache_instance = None
    yield
    cache_module._cache_instance = None


class DummyRedisClient:
    def __init__(self):
        self.db = 0
        self.store = {}
        self.closed = False

    def ping(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)

    def exists(self, key):
        return int(key in self.store)

    def keys(self, pattern):
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [key for key in self.store if key.startswith(prefix)]
        return [pattern] if pattern in self.store else []

    def info(self):
        return {
            "redis_version": "7.0.0",
            "connected_clients": 2,
            "used_memory_human": "1M",
            "db0": {"keys": 1},
            "db1": {"keys": 2},
        }

    def close(self):
        self.closed = True


class TestCacheManagerMemory:
    def test_memory_backend_roundtrip(self):
        cache = CacheManager()
        cache._redis_client = None

        payload = {"classe": "APC", "pagina": 1}

        assert cache.set("consulta", payload, ttl=120) is True
        assert cache.get("consulta") == payload
        assert cache.exists("consulta") is True

    def test_delete_and_clear_memory_backend(self):
        cache = CacheManager()
        cache._redis_client = None

        cache.set("a", {"x": 1})
        cache.set("b", {"x": 2})

        assert cache.delete("a") is True
        assert cache.exists("a") is False
        assert cache.clear() is True
        assert cache.exists("b") is False

    def test_get_returns_none_on_deserialize_error(self):
        cache = CacheManager()
        cache._redis_client = None
        cache._memory_cache[cache._build_key("broken")] = "not-json"

        assert cache.get("broken") is None

    def test_set_returns_false_on_serialize_error(self, monkeypatch):
        cache = CacheManager()
        cache._redis_client = None
        monkeypatch.setattr(
            cache, "_serialize", MagicMock(side_effect=TypeError("bad"))
        )

        assert cache.set("broken", object()) is False

    def test_delete_exists_and_clear_return_false_on_errors(self, monkeypatch):
        cache = CacheManager()
        failing_client = MagicMock()
        failing_client.delete.side_effect = RuntimeError("boom")
        failing_client.exists.side_effect = RuntimeError("boom")
        failing_client.keys.side_effect = RuntimeError("boom")
        cache._redis_client = failing_client

        assert cache.delete("x") is False
        assert cache.exists("x") is False
        assert cache.clear() is False

    def test_get_stats_for_memory_backend(self):
        cache = CacheManager(default_ttl=123, prefix="custom")
        cache._redis_client = None
        cache.set("a", {"ok": True})

        stats = cache.get_stats()

        assert stats["backend"] == "memory"
        assert stats["prefix"] == "custom"
        assert stats["default_ttl"] == 123
        assert stats["memory_cache_size"] == 1


class TestCacheManagerRedis:
    def test_init_uses_redis_when_available(self, monkeypatch):
        fake_redis = MagicMock()
        fake_redis.Redis.return_value = DummyRedisClient()
        monkeypatch.setattr(cache_module, "REDIS_AVAILABLE", True)
        monkeypatch.setattr(cache_module, "redis", fake_redis, raising=False)

        cache = CacheManager(prefix="redis-test")

        assert cache._redis_client is not None
        assert cache.get_stats()["backend"] == "redis"

    def test_init_falls_back_to_memory_when_redis_connection_fails(self, monkeypatch):
        fake_redis = MagicMock()
        fake_client = DummyRedisClient()
        fake_client.ping = MagicMock(side_effect=RuntimeError("offline"))
        fake_redis.Redis.return_value = fake_client
        monkeypatch.setattr(cache_module, "REDIS_AVAILABLE", True)
        monkeypatch.setattr(cache_module, "redis", fake_redis, raising=False)

        cache = CacheManager()

        # With lazy loading, need to trigger a cache operation to check connection
        cache.set("test", {"value": 1})

        assert cache._redis_client is None

    def test_redis_backend_roundtrip_and_close(self):
        cache = CacheManager()
        cache._redis_client = DummyRedisClient()

        payload = {"query": "tributario"}

        assert cache.set("redis-key", payload, ttl=30) is True
        assert cache.get("redis-key") == payload
        assert cache.exists("redis-key") is True
        assert cache.clear() is True
        assert cache.exists("redis-key") is False

        cache._redis_client = DummyRedisClient()
        cache.close()
        assert cache._redis_client.closed is True

    def test_get_stats_handles_redis_info_error(self):
        cache = CacheManager()
        failing_client = DummyRedisClient()
        failing_client.info = MagicMock(side_effect=RuntimeError("boom"))
        cache._redis_client = failing_client

        stats = cache.get_stats()

        assert stats["backend"] == "redis"
        assert stats["prefix"] == cache.prefix

    def test_get_stats_sums_keyspaces_across_all_dbs(self):
        cache = CacheManager()
        cache._redis_client = DummyRedisClient()

        stats = cache.get_stats()

        assert stats["keyspace_count"] == 3


class TestCacheHelpers:
    def test_build_key_with_single_string(self):
        assert CacheManager.build_key("processo:12345") == "processo:12345"

    def test_build_key_with_multiple_parts_and_sorted_dict(self):
        key1 = CacheManager.build_key("search", {"ano": 2024, "classe": "APC"})
        key2 = CacheManager.build_key("search", {"classe": "APC", "ano": 2024})

        assert key1 == key2
        assert key1.startswith("search:")

    def test_get_cache_returns_singleton_instance(self):
        cache1 = get_cache()
        cache2 = get_cache()

        assert cache1 is cache2


class TestCacheManagerLRU:
    """Test LRU cache eviction for in-memory backend."""

    def test_lru_eviction_when_limit_exceeded(self):
        """Test that oldest entries are removed when cache limit is exceeded."""
        cache = CacheManager()
        cache._redis_client = None
        cache._max_memory_items = 3  # Set small limit for testing

        # Fill cache to limit
        cache.set("key1", {"value": 1})
        cache.set("key2", {"value": 2})
        cache.set("key3", {"value": 3})

        assert cache.exists("key1") is True
        assert cache.exists("key2") is True
        assert cache.exists("key3") is True

        # Add one more item - should evict oldest (key1)
        cache.set("key4", {"value": 4})

        assert cache.exists("key1") is False  # Evicted
        assert cache.exists("key2") is True
        assert cache.exists("key3") is True
        assert cache.exists("key4") is True

    def test_lru_recency_update_on_existing_key(self):
        """Test that accessing/moving existing key updates its recency."""
        cache = CacheManager()
        cache._redis_client = None
        cache._max_memory_items = 3

        cache.set("key1", {"value": 1})
        cache.set("key2", {"value": 2})
        cache.set("key3", {"value": 3})

        # Access key1 (should make it most recently used)
        cache.get("key1")

        # Add new item - should evict key2 (oldest after key1 access)
        cache.set("key4", {"value": 4})

        assert cache.exists("key1") is True  # Still present (accessed)
        assert cache.exists("key2") is False  # Evicted (oldest)
        assert cache.exists("key3") is True
        assert cache.exists("key4") is True

    def test_exists_removes_expired_entry_from_memory_cache(self):
        """Test that exists() honors TTL expiration in memory backend."""
        cache = CacheManager()
        cache._redis_client = None

        cache.set("key1", {"value": 1}, ttl=1)

        assert cache.exists("key1") is True

        time.sleep(1.1)

        assert cache.exists("key1") is False
        assert cache.get("key1") is None

    def test_lru_recency_update_on_set_existing_key(self):
        """Test that updating existing key updates its recency."""
        cache = CacheManager()
        cache._redis_client = None
        cache._max_memory_items = 3

        cache.set("key1", {"value": 1})
        cache.set("key2", {"value": 2})
        cache.set("key3", {"value": 3})

        # Update key1 (should make it most recently used)
        cache.set("key1", {"value": 10})

        # Add new item - should evict key2 (oldest after key1 update)
        cache.set("key4", {"value": 4})

        assert cache.exists("key1") is True  # Still present (updated)
        assert cache.exists("key2") is False  # Evicted (oldest)
        assert cache.exists("key3") is True
        assert cache.exists("key4") is True


class TestCacheManagerLazyLoading:
    """Test lazy loading of Redis connection."""

    def test_connection_checked_on_first_get(self):
        """Test that Redis connection is checked on first get() call."""
        cache = CacheManager()
        fake_client = DummyRedisClient()
        cache._redis_client = fake_client

        # Connection should not be checked during __init__
        assert cache._connection_checked is False

        # First get should trigger connection check
        cache.get("test")

        assert cache._connection_checked is True

    def test_connection_checked_on_first_set(self):
        """Test that Redis connection is checked on first set() call."""
        cache = CacheManager()
        fake_client = DummyRedisClient()
        cache._redis_client = fake_client

        assert cache._connection_checked is False

        # First set should trigger connection check
        cache.set("test", {"value": 1})

        assert cache._connection_checked is True

    def test_connection_checked_on_first_delete(self):
        """Test that Redis connection is checked on first delete() call."""
        cache = CacheManager()
        fake_client = DummyRedisClient()
        cache._redis_client = fake_client

        assert cache._connection_checked is False

        # First delete should trigger connection check
        cache.delete("test")

        assert cache._connection_checked is True

    def test_connection_checked_on_first_exists(self):
        """Test that Redis connection is checked on first exists() call."""
        cache = CacheManager()
        fake_client = DummyRedisClient()
        cache._redis_client = fake_client

        assert cache._connection_checked is False

        # First exists should trigger connection check
        cache.exists("test")

        assert cache._connection_checked is True

    def test_lazy_loading_falls_back_to_memory_on_ping_failure(self, monkeypatch):
        """Test that failed ping falls back to memory cache."""
        cache = CacheManager()
        failing_client = DummyRedisClient()
        failing_client.ping = MagicMock(side_effect=RuntimeError("offline"))
        cache._redis_client = failing_client

        assert cache._connection_checked is False

        # First operation should trigger ping and fallback
        cache.set("test", {"value": 1})

        assert cache._connection_checked is True
        assert cache._redis_client is None  # Fallback to memory
        assert cache.get("test") == {"value": 1}  # Should still work
