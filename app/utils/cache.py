"""
Cache manager for TJDFT API.

Provides a unified caching interface with Redis support and in-memory fallback.
"""

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Try to import Redis, but make it optional
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Using in-memory cache fallback.")


class CacheManager:
    """
    Unified cache manager with Redis or in-memory storage.
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,
        prefix: str = "tjdft",
    ):
        """
        Initialize cache manager.

        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            redis_password: Redis password (optional)
            redis_url: Full Redis URL (overrides host/port/db)
            default_ttl: Default time-to-live in seconds (default: 3600 = 1 hour)
            prefix: Key prefix for cache entries
        """
        self.default_ttl = default_ttl
        self.prefix = prefix
        self._redis_client: Optional[Any] = None
        self._memory_cache: OrderedDict = OrderedDict()
        self._max_memory_items = 1000  # LRU limit for in-memory cache
        self._connection_checked = False
        self._connection_lock = threading.Lock()  # Protects _check_connection()

        if REDIS_AVAILABLE:
            try:
                if redis_url:
                    self._redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                    )
                else:
                    self._redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        password=redis_password,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                    )
                # Defer connection check to first use (lazy loading)
                # Sanitize URL for logging (remove password)
                if redis_url:
                    parsed = urlparse(redis_url)
                    safe_host = (
                        f"{parsed.hostname}:{parsed.port}"
                        if parsed.port
                        else parsed.hostname
                    )
                    logger.info(f"Redis client configured for {safe_host}")
                else:
                    logger.info(f"Redis client configured for {redis_host}:{redis_port}")
            except Exception as e:
                logger.warning(
                    f"Failed to configure Redis: {e}. Using in-memory cache."
                )
                self._redis_client = None
        else:
            logger.info("Using in-memory cache (Redis not available)")

    def _build_key(self, key: str) -> str:
        """
        Build full cache key with prefix.

        Args:
            key: Base key

        Returns:
            Full key with prefix
        """
        return f"{self.prefix}:{key}"

    def _check_connection(self) -> None:
        """
        Check Redis connection on first use (lazy loading).

        This method is called on the first cache operation to verify
        that the Redis connection is working. If not, it falls back
        to in-memory cache.

        Uses threading.Lock to prevent race condition when multiple
        threads call this method concurrently.
        """
        if self._connection_checked or not self._redis_client:
            return

        with self._connection_lock:
            # Double-check after acquiring lock
            if self._connection_checked or not self._redis_client:
                return

            try:
                self._redis_client.ping()
                self._connection_checked = True
                logger.debug("Redis connection verified on first use")
            except Exception as e:
                logger.warning(
                    f"Redis connection check failed on first use: {e}. "
                    "Falling back to in-memory cache."
                )
                self._redis_client = None
                self._connection_checked = True

    def _serialize(self, value: Any) -> str:
        """
        Serialize value to JSON string.

        Args:
            value: Value to serialize

        Returns:
            JSON string
        """
        return json.dumps(value)

    def _deserialize(self, value: str) -> Any:
        """
        Deserialize JSON string to Python object.

        Args:
            value: JSON string to deserialize

        Returns:
            Python object
        """
        return json.loads(value)

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key (without prefix)

        Returns:
            Cached value or None if not found or expired
        """
        # Check connection on first use (lazy loading)
        self._check_connection()

        full_key = self._build_key(key)

        try:
            if self._redis_client:
                value = self._redis_client.get(full_key)
                if value is not None:
                    return self._deserialize(value)
            else:
                if full_key in self._memory_cache:
                    entry = self._memory_cache[full_key]
                    # Check if expired (entry is tuple of (expiration_time, value))
                    if isinstance(entry, tuple):
                        expiration_time, serialized_value = entry
                        if time.time() > expiration_time:
                            # Entry expired, remove it
                            del self._memory_cache[full_key]
                            logger.debug(f"Cache entry expired: {full_key}")
                            return None
                        # Move to end (most recently used)
                        self._memory_cache.move_to_end(full_key)
                        return self._deserialize(serialized_value)
                    else:
                        # Legacy entry without expiration, return as-is
                        self._memory_cache.move_to_end(full_key)
                        return self._deserialize(entry)

            return None

        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key (without prefix)
            value: Value to cache
            ttl: Time-to-live in seconds (uses default_ttl if None)

        Returns:
            True if successful, False otherwise
        """
        # Check connection on first use (lazy loading)
        self._check_connection()

        full_key = self._build_key(key)
        ttl = ttl if ttl is not None else self.default_ttl

        try:
            serialized_value = self._serialize(value)

            if self._redis_client:
                self._redis_client.setex(full_key, ttl, serialized_value)
            else:
                # Calculate expiration time
                expiration_time = time.time() + ttl

                # If key already exists, move to end (most recently used)
                if full_key in self._memory_cache:
                    self._memory_cache.move_to_end(full_key)

                # Add to cache as tuple of (expiration_time, serialized_value)
                self._memory_cache[full_key] = (expiration_time, serialized_value)
                # Enforce LRU limit - remove oldest if over limit
                if len(self._memory_cache) > self._max_memory_items:
                    self._memory_cache.popitem(last=False)
                    logger.debug(
                        f"LRU cache limit reached ({self._max_memory_items}), "
                        "oldest entry removed"
                    )

            logger.debug(f"Cached key: {full_key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key (without prefix)

        Returns:
            True if successful, False otherwise
        """
        # Check connection on first use (lazy loading)
        self._check_connection()

        full_key = self._build_key(key)

        try:
            if self._redis_client:
                self._redis_client.delete(full_key)
            else:
                if full_key in self._memory_cache:
                    del self._memory_cache[full_key]

            logger.debug(f"Deleted cache key: {full_key}")
            return True

        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache and is not expired.

        Args:
            key: Cache key (without prefix)

        Returns:
            True if key exists and is not expired, False otherwise
        """
        # Check connection on first use (lazy loading)
        self._check_connection()

        full_key = self._build_key(key)

        try:
            if self._redis_client:
                return bool(self._redis_client.exists(full_key))
            else:
                if full_key not in self._memory_cache:
                    return False

                # Check if expired (entry is tuple of (expiration_time, value))
                entry = self._memory_cache[full_key]
                if isinstance(entry, tuple):
                    expiration_time, _ = entry
                    if time.time() > expiration_time:
                        # Entry expired, remove it
                        del self._memory_cache[full_key]
                        logger.debug(f"Cache entry expired on exists(): {full_key}")
                        return False
                return True

        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False

    def clear(self) -> bool:
        """
        Clear all cache entries with the configured prefix.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self._redis_client:
                # Get all keys with prefix
                keys = self._redis_client.keys(f"{self.prefix}:*")
                if keys:
                    self._redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries")
            else:
                count = len(self._memory_cache)
                self._memory_cache.clear()
                logger.info(f"Cleared {count} cache entries from memory")

            return True

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    @staticmethod
    def build_key(*args: Union[str, int, dict]) -> str:
        """
        Build a cache key from multiple components.

        Args:
            *args: Variable number of key components (strings, ints, or dicts)

        Returns:
            Hash-based cache key

        Examples:
            >>> CacheManager.build_key("processo", "12345")
            'processo:12345'
            >>> CacheManager.build_key("search", {"classe": "APC", "ano": 2024})
            'search:a1b2c3d4'
        """
        if len(args) == 1 and isinstance(args[0], str):
            return args[0]

        # For multiple arguments or complex types, create a hash
        key_parts = []
        for arg in args:
            if isinstance(arg, dict):
                # Sort dict keys for consistent hashing
                sorted_dict = json.dumps(arg, sort_keys=True)
                key_hash = hashlib.md5(sorted_dict.encode()).hexdigest()[:8]
                key_parts.append(key_hash)
            else:
                key_parts.append(str(arg))

        return ":".join(key_parts)

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "backend": "redis" if self._redis_client else "memory",
            "prefix": self.prefix,
            "default_ttl": self.default_ttl,
        }

        if self._redis_client:
            try:
                info = self._redis_client.info()
                stats.update(
                    {
                        "redis_version": info.get("redis_version"),
                        "connected_clients": info.get("connected_clients"),
                        "used_memory_human": info.get("used_memory_human"),
                        "keyspace_count": sum(
                            info.get(f"db{i}", {}).get("keys", 0) for i in range(16)
                        ),
                    }
                )
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
        else:
            stats["memory_cache_size"] = len(self._memory_cache)

        return stats

    def close(self) -> None:
        """
        Close Redis connection if exists.
        """
        if self._redis_client:
            try:
                self._redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")


# Global cache instance
_cache_instance: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_cache() -> CacheManager:
    """
    Get global cache manager instance.

    Uses double-checked locking pattern for thread safety.

    Returns:
        CacheManager instance
    """
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            # Double-check after acquiring lock
            if _cache_instance is None:
                _cache_instance = CacheManager()
    return _cache_instance
