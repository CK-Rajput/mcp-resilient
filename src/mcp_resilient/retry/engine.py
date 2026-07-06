from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

from mcp_resilient.core.config import RetryConfig
from mcp_resilient.core.exceptions import RetryExhaustedError
from mcp_resilient.retry.backoff import compute_delay
from mcp_resilient.retry.budget import RetryBudget

T = TypeVar("T")


@dataclass
class RetryOutcome:
    result: Any
    attempts: int
    total_delay_seconds: float


async def run_with_retry(
    fn: Callable[[], Awaitable[T]],
    config: RetryConfig,
    tool_name: str,
    retry_budget: RetryBudget | None = None,
) -> RetryOutcome:
    """Run an async callable with retry + backoff.

    Each attempt is wrapped in `asyncio.wait_for` using `config.timeout_seconds`
    so a hung call can't stall the whole retry budget.

    Raises RetryExhaustedError (wrapping the last underlying exception) once
    `max_attempts` is reached or if the retry budget is exhausted.
    """
    last_error: BaseException | None = None
    delay: float | None = None
    total_delay = 0.0

    for attempt in range(1, config.max_attempts + 1):
        try:
            result = await asyncio.wait_for(fn(), timeout=config.timeout_seconds)
            return RetryOutcome(result=result, attempts=attempt, total_delay_seconds=total_delay)
        except config.retry_on as exc:  # type: ignore[misc]
            last_error = exc
            if attempt < config.max_attempts:
                if retry_budget and not retry_budget.can_retry():
                    # Budget exhausted, raise early
                    raise RetryExhaustedError(
                        tool_name, attempt, ConnectionError("Retry budget exhausted")
                    ) from exc
                if retry_budget:
                    retry_budget.record_retry()
                delay = compute_delay(config.backoff, attempt, delay)
                total_delay += delay
                await asyncio.sleep(delay)

    assert last_error is not None
    raise RetryExhaustedError(tool_name, config.max_attempts, last_error)
