from __future__ import annotations

import pytest

from mcp_resilient.core.config import BackoffConfig, RetryConfig
from mcp_resilient.core.exceptions import RetryExhaustedError
from mcp_resilient.retry.engine import run_with_retry


async def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("boom")
        return "ok"

    config = RetryConfig(max_attempts=5, backoff=BackoffConfig(base_delay=0.01, max_delay=0.02))
    outcome = await run_with_retry(flaky, config, "test_tool")

    assert outcome.result == "ok"
    assert outcome.attempts == 3


async def test_retry_exhausts_and_raises():
    async def always_fails():
        raise ConnectionError("nope")

    config = RetryConfig(max_attempts=3, backoff=BackoffConfig(base_delay=0.01, max_delay=0.02))

    with pytest.raises(RetryExhaustedError) as exc_info:
        await run_with_retry(always_fails, config, "test_tool")

    assert exc_info.value.attempts == 3


async def test_retry_respects_per_attempt_timeout():
    import asyncio

    async def hangs():
        await asyncio.sleep(1)
        return "should not reach here"

    config = RetryConfig(
        max_attempts=1, timeout_seconds=0.05, backoff=BackoffConfig(base_delay=0.01)
    )

    with pytest.raises(RetryExhaustedError):
        await run_with_retry(hangs, config, "slow_tool")
