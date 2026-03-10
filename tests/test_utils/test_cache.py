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
        prefix = pattern[:-1]
        return [key for key in self.store if key.startswith(prefix)]

    def info(self):
        return {
            "redis_version": "7.0.0",
            "connected_clients": 2,
            "used_memory_human": "1M",
            "db0": {"keys": 1},
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
        monkeypatch.setattr(cache, "_serialize", MagicMock(side_effect=TypeError("bad")))

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
        assert stats["prefix"] == "tjdft"


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
