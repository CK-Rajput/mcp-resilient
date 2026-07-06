from __future__ import annotations

import asyncio
from typing import Any

from mcp_resilient.storage.base import StateStore


class InMemoryStateStore(StateStore):
    """Default backend. Good for single-process agents and tests.

    Not shared across processes — use RedisStateStore when running
    multiple agent instances that should share one circuit state.
    """

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> dict[str, Any] | None:
        async with self._lock:
            return self._data.get(key)

    async def set(self, key: str, value: dict[str, Any]) -> None:
        async with self._lock:
            self._data[key] = value

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)
