"""Circuit breaker demo — shows CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""

import asyncio

from mcp_resilient import CircuitBreakerConfig, ReliabilityConfig, RetryConfig, mcp_reliable
from mcp_resilient.core.exceptions import CircuitOpenError

config = ReliabilityConfig(
    tool_name="unstable_tool",
    retry=RetryConfig(max_attempts=1),
    circuit_breaker=CircuitBreakerConfig(failure_threshold=3, cooldown_seconds=1),
)

call_count = 0


@mcp_reliable(config)
async def call_unstable_tool() -> str:
    global call_count
    call_count += 1
    if call_count <= 3:
        raise TimeoutError("simulated failure")
    return "recovered"


async def main():
    for i in range(7):
        try:
            result = await call_unstable_tool()
            print(f"call {i}: success -> {result}")
        except CircuitOpenError as e:
            print(f"call {i}: blocked -> {e}")
        except Exception as e:
            print(f"call {i}: failed -> {e!r}")
        await asyncio.sleep(0.4)


if __name__ == "__main__":
    asyncio.run(main())
