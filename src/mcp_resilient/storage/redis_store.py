from __future__ import annotations

import json
from typing import Any

from mcp_resilient.storage.base import StateStore

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore


class RedisStateStore(StateStore):
    """Distributed backend for multi-process / multi-instance agent
    deployments — every instance shares the same circuit state, so a
    tool that trips on pod A stays tripped for pods B and C too.

    Requires: pip install mcp-resilient[redis]
    """

    def __init__(self, url: str = "redis://localhost:6379/0", prefix: str = "mcp_resilient:"):
        if redis is None:
            raise ImportError("redis package not installed. Run: pip install mcp-resilient[redis]")
        self._client = redis.from_url(url, decode_responses=True)
        self._prefix = prefix

    async def get(self, key: str) -> dict[str, Any] | None:
        raw = await self._client.get(self._prefix + key)
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: dict[str, Any]) -> None:
        await self._client.set(self._prefix + key, json.dumps(value))

    async def delete(self, key: str) -> None:
        await self._client.delete(self._prefix + key)
