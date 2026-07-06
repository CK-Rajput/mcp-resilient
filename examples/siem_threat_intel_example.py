"""Real-world pattern from a SIEM/SecOps context: threat-intel enrichment
during incident correlation, with a paid primary vendor API, a free
backup API, and a cost budget so retries can't blow past what the
primary vendor allows per minute.
"""

import asyncio

from mcp_resilient import (
    CircuitBreakerConfig,
    FallbackConfig,
    ReliabilityConfig,
    RetryConfig,
    mcp_reliable,
)

config = ReliabilityConfig(
    tool_name="threat_intel_primary",
    retry=RetryConfig(max_attempts=3, timeout_seconds=4),
    circuit_breaker=CircuitBreakerConfig(failure_threshold=5, cost_budget=2.00, window_seconds=60),
    fallback=FallbackConfig(enabled=True, tool_chain=["threat_intel_backup"]),
)


async def query_vendor_api(ioc: str, tool_name: str) -> dict:
    # Stand-in for a real HTTP call to a threat-intel vendor.
    if tool_name == "threat_intel_primary":
        raise TimeoutError("primary vendor rate-limited")
    return {"ioc": ioc, "source": tool_name, "risk_score": 0.82}


@mcp_reliable(config, cost_fn=lambda _: 0.02)  # $0.02 per primary-vendor call
async def enrich_ioc(ioc: str, tool_name: str = "threat_intel_primary") -> dict:
    return await query_vendor_api(ioc, tool_name)


async def main():
    result = await enrich_ioc("185.220.101.7")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
