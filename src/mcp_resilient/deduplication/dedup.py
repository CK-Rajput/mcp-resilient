from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, Awaitable, Callable, TypeVar

from mcp_resilient.core.config import DeduplicationConfig

T = TypeVar("T")


class RequestDeduplicator:
    """Coalesces identical concurrent executions to run only once."""

    def __init__(self, config: DeduplicationConfig):
        self.config = config
        self.in_flight: dict[str, asyncio.Future[Any]] = {}

    def generate_key(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
        try:
            serialized = json.dumps((args, kwargs), sort_keys=True, default=repr)
        except Exception:  # noqa: BLE001
            serialized = str(args) + str(sorted(kwargs.items()))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def execute(self, key: str, fn: Callable[[], Awaitable[T]]) -> T:
        if not self.config.enabled:
            return await fn()

        if key in self.in_flight:
            return await self.in_flight[key]

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.in_flight[key] = future

        try:
            result = await fn()
            future.set_result(result)
            return result
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            self.in_flight.pop(key, None)


_deduplicators: dict[str, RequestDeduplicator] = {}


def get_deduplicator(tool_name: str, config: DeduplicationConfig) -> RequestDeduplicator:
    if tool_name not in _deduplicators:
        _deduplicators[tool_name] = RequestDeduplicator(config)
    return _deduplicators[tool_name]
