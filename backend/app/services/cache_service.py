"""
Redis-based caching service for external API responses.
Gracefully degrades when Redis is unavailable.
"""

import hashlib
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheService:
    """Lightweight Redis cache wrapper with fallback."""

    def __init__(self, redis_url: str = ""):
        self._client = None
        self._enabled = False
        self._redis_url = redis_url or "redis://localhost:6379/0"

    async def initialize(self):
        if not REDIS_AVAILABLE:
            logger.info("Redis not available — caching disabled")
            return
        try:
            self._client = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await self._client.ping()
            self._enabled = True
            logger.info("Redis cache connected at %s", self._redis_url)
        except Exception as exc:
            logger.warning("Redis connection failed — caching disabled: %s", exc)
            self._client = None

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def get(self, key: str) -> Optional[dict]:
        if not self._enabled or not self._client:
            return None
        try:
            data = await self._client.get(key)
            return json.loads(data) if data else None
        except Exception as exc:
            logger.debug("Cache get failed: %s", exc)
            return None

    async def set(self, key: str, value: dict, ttl: int = 3600) -> bool:
        if not self._enabled or not self._client:
            return False
        try:
            await self._client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as exc:
            logger.debug("Cache set failed: %s", exc)
            return False

    async def delete(self, key: str) -> bool:
        if not self._enabled or not self._client:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception as exc:
            logger.debug("Cache delete failed: %s", exc)
            return False

    def _make_key(self, prefix: str, *args) -> str:
        raw = f"{prefix}:{':'.join(str(a) for a in args)}"
        return f"sta:{hashlib.sha256(raw.encode()).hexdigest()[:32]}"

    async def get_or_set(
        self, prefix: str, args: tuple, fetch_fn, ttl: int = 3600
    ) -> tuple[dict, str]:
        key = self._make_key(prefix, *args)
        cached = await self.get(key)
        if cached is not None:
            return cached, "cache"
        result = await fetch_fn()
        await self.set(key, result, ttl=ttl)
        return result, "api"


_cache_service: Optional[CacheService] = None


def get_cache() -> CacheService:
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


async def init_cache(redis_url: str = ""):
    svc = get_cache()
    await svc.initialize()
    return svc
