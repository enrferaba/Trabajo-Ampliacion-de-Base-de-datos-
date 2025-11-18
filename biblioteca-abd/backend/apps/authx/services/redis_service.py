from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional

import redis
from django.conf import settings


@dataclass
class RedisClient:
    url: str = settings.REDIS_URL

    @property
    def client(self) -> redis.Redis:
        return redis.from_url(self.url, decode_responses=True)


redis_client = RedisClient()


def _safe_execute(func, default=None):
    try:
        return func()
    except redis.RedisError:
        return default


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    serialized = json.dumps(value)
    ttl = ttl or settings.CACHE_TTL_SECONDS
    _safe_execute(lambda: redis_client.client.setex(key, ttl, serialized))


def cache_delete(key: str) -> None:
    _safe_execute(lambda: redis_client.client.delete(key))


def cache_get(key: str) -> Optional[Any]:
    data = _safe_execute(lambda: redis_client.client.get(key))
    if data is None:
        return None
    return json.loads(data)


def rate_limit_hit(scope: str, identifier: str) -> bool:
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    max_requests = settings.RATE_LIMIT_MAX_REQUESTS
    key = f"ratelimit:{scope}:{identifier}:{window}"
    result = _safe_execute(
        lambda: redis_client.client.pipeline().incr(key, 1).expire(key, window, nx=True).execute(),
        default=[1, None],
    )
    current = result[0] if isinstance(result, (list, tuple)) else 1
    return int(current) > max_requests


def anti_spam_check(user_id: str, max_events: int = 5, window: int = 300) -> bool:
    key = f"antispam:reviews:{user_id}"
    _safe_execute(
        lambda: redis_client.client.pipeline()
        .lpush(key, "1")
        .ltrim(key, 0, max_events - 1)
        .expire(key, window, nx=True)
        .execute()
    )
    events_count = _safe_execute(lambda: redis_client.client.llen(key), default=0)
    return events_count > max_events


def cache_key_for_books(params: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    return f"cache:books:list:{digest}"


def invalidate_books_cache() -> None:
    def _invalidate():
        client = redis_client.client
        keys = client.keys("cache:books:list:*")
        if keys:
            client.delete(*keys)

    _safe_execute(_invalidate)


def publish_event(event: str, payload: dict[str, Any]) -> None:
    _safe_execute(lambda: redis_client.client.publish("events:biblioteca", json.dumps({"event": event, "payload": payload})))
