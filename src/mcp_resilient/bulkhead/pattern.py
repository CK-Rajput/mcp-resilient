from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

from mcp_resilient.core.config import BulkheadConfig
from mcp_resilient.core.exceptions import BulkheadFullError

T = TypeVar("T")


class Bulkhead:
    """Limits the concurrency of tool calls using asyncio.Semaphore."""

    def __init__(self, tool_name: str, config: BulkheadConfig):
        self.tool_name = tool_name
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent_calls)

    async def execute(self, fn: Callable[[], Awaitable[T]]) -> T:
        if not self.config.enabled:
            return await fn()

        acquired = False
        try:
            if self.config.max_queue_time_seconds is not None:
                try:
                    await asyncio.wait_for(
                        self.semaphore.acquire(),
                        timeout=self.config.max_queue_time_seconds,
                    )
                    acquired = True
                except asyncio.TimeoutError:
                    raise BulkheadFullError(self.tool_name, self.config.max_concurrent_calls) from None
            else:
                await self.semaphore.acquire()
                acquired = True

            return await fn()
        finally:
            if acquired:
                self.semaphore.release()
