# Manual Testing Guide - Performance Optimizations

This guide provides step-by-step instructions for manually testing the performance optimizations implemented in the PR.

## Prerequisites

1. Start the API server:
```bash
uvicorn app.main:app --reload
```

2. Have Redis running (optional - for testing fallback):
```bash
redis-server
```

## Test 1: Verify get_cache() Singleton Usage

### Objective
Confirm that the search endpoint uses `get_cache()` singleton instead of creating new Redis connections per request.

### Steps

1. Check the endpoint implementation:
```bash
grep -n "get_cache\|CacheManager()" app/api/v1/endpoints/busca.py
```

**Expected Result:**
- Should see `cache = get_cache()` (line ~51)
- Should NOT see `cache = CacheManager()`

2. Make multiple search requests:
```bash
curl -X POST "http://localhost:8000/api/v1/busca/" \
  -H "Content-Type: application/json" \
  -d '{"query": "tributário", "pagina": 1, "tamanho": 5}'

curl -X POST "http://localhost:8000/api/v1/busca/" \
  -H "Content-Type: application/json" \
  -d '{"query": "trabalhista", "pagina": 1, "tamanho": 5}'
```

**Expected Result:**
- Both requests complete successfully
- No duplicate Redis connection errors in logs
- Response time consistent (no 5-50ms penalty per request)

---

## Test 2: Verify Redis Connection Fallback (Lazy Loading)

### Objective
Confirm that the cache gracefully degrades to in-memory mode if Redis is unavailable.

### Scenario A: Redis Available

1. Ensure Redis is running:
```bash
redis-cli ping  # Should return PONG
```

2. Make a search request:
```bash
curl -X POST "http://localhost:8000/api/v1/busca/" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "pagina": 1, "tamanho": 5}'
```

**Expected Result:**
- Request succeeds
- Logs show: "Redis client configured for localhost:6379"
- On first request: "Redis connection verified on first use"

### Scenario B: Redis Unavailable

1. Stop Redis:
```bash
redis-cli shutdown  # OR kill redis-server
```

2. Make a search request:
```bash
curl -X POST "http://localhost:8000/api/v1/busca/" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "pagina": 1, "tamanho": 5}'
```

**Expected Result:**
- Request still succeeds (graceful degradation)
- Logs show: "Redis connection check failed on first use: Failing back to in-memory cache."
- No error returned to client

### Scenario C: Redis Becomes Available During Runtime

1. Start with Redis stopped, make a request (in-memory mode)
2. Start Redis
3. Make another request

**Expected Result:**
- First request uses in-memory cache
- Second request logs connection check and may use Redis (depends on implementation)

---

## Test 3: Verify LRU Cache Eviction (In-Memory Mode)

### Objective
Confirm that the in-memory cache correctly evicts oldest entries when the limit (1000 items) is reached.

### Setup

Create a simple test script `test_lru.py`:

```python
from app.utils.cache import CacheManager

# Create cache with small limit for testing
cache = CacheManager()
cache._redis_client = None  # Force in-memory mode
cache._max_memory_items = 5  # Set very small limit

print("Testing LRU eviction...")

# Fill cache to limit
for i in range(5):
    cache.set(f"key{i}", {"value": i})
    print(f"Added key{i}, cache size: {len(cache._memory_cache)}")

# All keys should exist
for i in range(5):
    exists = cache.exists(f"key{i}")
    print(f"key{i} exists: {exists}")

# Add one more item - should evict key0 (oldest)
cache.set("key5", {"value": 5})
print(f"\nAfter adding key5, cache size: {len(cache._memory_cache)}")

# Check eviction
print("\nChecking eviction:")
for i in range(6):
    exists = cache.exists(f"key{i}")
    print(f"key{i} exists: {exists}")

print("\n✅ LRU Test completed!")
```

### Run Test

```bash
python3 test_lru.py
```

**Expected Result:**
```
Added key0, cache size: 1
Added key1, cache size: 2
Added key2, cache size: 3
Added key3, cache size: 4
Added key4, cache size: 5
key0 exists: True
key1 exists: True
key2 exists: True
key3 exists: True
key4 exists: True

After adding key5, cache size: 5

Checking eviction:
key0 exists: False  ← Evicted (oldest)
key1 exists: True
key2 exists: True
key3 exists: True
key4 exists: True
key5 exists: True
```

---

## Test 4: Verify Metadata Cache with 24h TTL

### Objective
Confirm that reference data (relatores, classes, orgãos) is cached with 24h TTL.

### Steps

1. Create test script `test_metadata_cache.py`:

```python
from app.utils.cache import get_cache
from app.utils.filtros import load_referencia, REFERENCIA_DATA_CACHE_KEY, clear_referencia_cache

print("Testing metadata cache...")

# Clear cache first
clear_referencia_cache()
cache = get_cache()

# First load - should hit file
print("\n1. First load (from file):")
cache.delete(REFERENCIA_DATA_CACHE_KEY)
data1 = load_referencia()
print(f"   Loaded {len(data1.get('relatores', []))} relatores")

# Second load - should hit cache
print("\n2. Second load (from cache):")
data2 = load_referencia()
print(f"   Loaded {len(data2.get('relatores', []))} relatores")

# Verify cache TTL
print(f"\n3. Cache key: {REFERENCIA_DATA_CACHE_KEY}")
print(f"   Data is identical: {data1 == data2}")

print("\n✅ Metadata cache test completed!")
```

2. Run test:
```bash
python3 test_metadata_cache.py
```

**Expected Result:**
- First load loads from file (logs show file path)
- Second load loads from cache (logs show "Reference data loaded from cache")
- Data is identical between both loads
- Cache key is "referencia:data"

---

## Test 5: Verify Synchronous Enrichment (No Async Overhead)

### Objective
Confirm that enrichment uses synchronous list comprehension instead of async overhead.

### Steps

1. Check the implementation:
```bash
grep -A 20 "Enrich data with instancia" app/services/busca_service.py
```

**Expected Result:**
- Should see list comprehension with `for registro in dados`
- Should NOT see `async def enriquecer_registro` or `asyncio.gather()`
- Should NOT see `import asyncio` at top of file

2. Verify import:
```bash
head -20 app/services/busca_service.py | grep -i "asyncio"
```

**Expected Result:**
- No output (asyncio import removed)

---

## Test 6: Performance Comparison (Optional)

### Objective
Compare response times before and after optimizations.

### Method

1. With Redis available, make 10 requests:
```bash
for i in {1..10}; do
  curl -X POST "http://localhost:8000/api/v1/busca/" \
    -H "Content-Type: application/json" \
    -d '{"query": "tributário", "pagina": 1, "tamanho": 20}' \
    -w "\nResponse time: %{time_total}s\n"
done
```

2. Check logs for cache hits:
```bash
# In server logs, look for:
# - "Reference data loaded from cache"
# - "Redis connection verified on first use"
# - "LRU cache limit reached"
```

---

## Cleanup

Remove test scripts:
```bash
rm -f test_lru.py test_metadata_cache.py
```

---

## Test Results Summary

Mark tests as complete in the PR description:

- [x] Manual testing of search endpoints
- [x] Verify Redis connection fallback works
- [x] Check LRU eviction in in-memory mode

---

## Troubleshooting

### Issue: Server won't start
**Solution**: Check if port 8000 is in use:
```bash
lsof -i :8000
```

### Issue: Redis connection errors
**Solution**: Verify Redis is running:
```bash
redis-cli ping
```

### Issue: Module not found errors
**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```
