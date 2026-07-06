from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

from mcp_resilient.core.config import HedgedConfig

T = TypeVar("T")


async def run_with_hedges(
    fn: Callable[[], Awaitable[T]], config: HedgedConfig
) -> T:
    """Runs a function using the hedged requests pattern.

    If the primary call is not done after delay_seconds, spawns
    up to `hedges` additional concurrent tasks, returning the first
    successful outcome and cancelling the remaining ones.
    """
    if not config.enabled or config.hedges <= 0:
        return await fn()

    pending_tasks = set()
    completed_event = asyncio.Event()
    results: list[T] = []
    errors: list[BaseException] = []

    async def worker() -> None:
        try:
            res = await fn()
            results.append(res)
            completed_event.set()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
            if len(errors) >= (config.hedges + 1):
                completed_event.set()

    primary_task = asyncio.create_task(worker())
    pending_tasks.add(primary_task)

    for _ in range(config.hedges):
        try:
            await asyncio.wait_for(completed_event.wait(), timeout=config.delay_seconds)
            break
        except asyncio.TimeoutError:
            hedge_task = asyncio.create_task(worker())
            pending_tasks.add(hedge_task)

    await completed_event.wait()

    for task in pending_tasks:
        if not task.done():
            task.cancel()

    if pending_tasks:
        await asyncio.gather(*pending_tasks, return_exceptions=True)

    if results:
        return results[0]

    if errors:
        raise errors[-1]

    raise RuntimeError("Hedged requests failed with no results and no errors.")
