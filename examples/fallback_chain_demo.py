"""Fallback chain demo — primary tool fails, router moves to backup.

Note: the wrapped function accepts `tool_name` and dispatches on it —
that's how mcp-resilient routes each hop of the fallback chain to a
different underlying tool without needing a separate decorated function
per tool.
"""

import asyncio

from mcp_resilient import FallbackConfig, ReliabilityConfig, RetryConfig, mcp_reliable

config = ReliabilityConfig(
    tool_name="primary_search",
    retry=RetryConfig(max_attempts=1),
    fallback=FallbackConfig(enabled=True, tool_chain=["backup_search"]),
)


@mcp_reliable(config)
async def search(query: str, tool_name: str = "primary_search") -> str:
    if tool_name == "primary_search":
        raise ConnectionError("primary_search is down")
    return f"[{tool_name}] results for: {query}"


async def main():
    result = await search("noida ai jobs")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
