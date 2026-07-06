"""Basic retry example — no circuit breaker, no fallback."""

import asyncio
import random

from mcp_resilient import ReliabilityConfig, RetryConfig, mcp_reliable

config = ReliabilityConfig(
    tool_name="flaky_api",
    retry=RetryConfig(max_attempts=4),
)


@mcp_reliable(config)
async def call_flaky_api(payload: str) -> str:
    if random.random() < 0.6:
        raise ConnectionError("upstream timeout")
    return f"ok: {payload}"


async def main():
    result = await call_flaky_api("hello")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
