from __future__ import annotations

import os
import tempfile
from mcp_resilient import (
    ReliabilityConfig,
    RetryConfig,
    CircuitBreakerConfig,
    FallbackConfig,
    mcp_reliable,
)


# Mock MCP client for documentation sync testing
class MockMCPClient:
    async def call_tool(self, name: str, arguments: dict):
        if (
            name == "flaky_api"
            or name == "threat_intel_lookup"
            or name == "threat_intel"
        ):
            return {"status": "ok", "result": "mocked_data"}
        elif name == "primary_search":
            raise ConnectionError("primary offline")
        elif name == "backup_search":
            return "backup_search_results"
        return {"status": "success"}


mcp_client = MockMCPClient()


async def test_readme_first_example():
    # Example from README.md
    config = ReliabilityConfig(tool_name="threat_intel_lookup")

    @mcp_reliable(config)
    async def call_threat_intel(ioc: str):
        return await mcp_client.call_tool("threat_intel_lookup", {"ioc": ioc})

    result = await call_threat_intel("8.8.8.8")
    assert result == {"status": "ok", "result": "mocked_data"}


async def test_quickstart_retry_only():
    # Example from docs/quickstart.md (Retry only)
    config = ReliabilityConfig(
        tool_name="flaky_api",
        retry=RetryConfig(max_attempts=4),
    )

    @mcp_reliable(config)
    async def call_flaky_api(payload: str) -> str:
        return await mcp_client.call_tool("flaky_api", {"payload": payload})

    result = await call_flaky_api("test_payload")
    assert result == {"status": "ok", "result": "mocked_data"}


async def test_quickstart_circuit_breaker():
    # Example from docs/quickstart.md (+ Circuit breaker)
    config = ReliabilityConfig(
        tool_name="threat_intel",
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=5,
            cost_budget=2.00,
            window_seconds=60,
            cooldown_seconds=30,
        ),
    )

    @mcp_reliable(config, cost_fn=lambda result: 0.02)
    async def call_threat_intel(ioc: str) -> dict:
        return await mcp_client.call_tool("threat_intel", {"ioc": ioc})

    result = await call_threat_intel("8.8.8.8")
    assert result == {"status": "ok", "result": "mocked_data"}


async def test_quickstart_fallback_chain():
    # Example from docs/quickstart.md (+ Fallback chain)
    config = ReliabilityConfig(
        tool_name="primary_search",
        fallback=FallbackConfig(enabled=True, tool_chain=["backup_search"]),
    )

    @mcp_reliable(config)
    async def search(query: str, tool_name: str = "primary_search") -> str:
        return await mcp_client.call_tool(tool_name, {"query": query})

    result = await search("testing fallback")
    assert result == "backup_search_results"


async def test_quickstart_yaml_policy():
    # Example from docs/quickstart.md (YAML policy files)
    yaml_content = """
tool_name: threat_intel_primary
retry:
  max_attempts: 3
circuit_breaker:
  failure_threshold: 5
  cost_budget: 2.0
fallback:
  enabled: true
  tool_chain: ["threat_intel_backup"]
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config = ReliabilityConfig.from_yaml(temp_path)
        assert config.tool_name == "threat_intel_primary"
        assert config.retry.max_attempts == 3
        assert config.circuit_breaker.failure_threshold == 5
        assert config.circuit_breaker.cost_budget == 2.0
        assert config.fallback.enabled is True
        assert config.fallback.tool_chain == ["threat_intel_backup"]
    finally:
        os.remove(temp_path)
