# Quickstart

## Install

```bash
pip install mcp-resilient
```

## Retry only

```python
from mcp_resilient import ReliabilityConfig, RetryConfig, mcp_reliable

config = ReliabilityConfig(
    tool_name="flaky_api",
    retry=RetryConfig(max_attempts=4),
)

@mcp_reliable(config)
async def call_flaky_api(payload: str) -> str:
    return await mcp_client.call_tool("flaky_api", {"payload": payload})
```

## + Circuit breaker (cost-aware)

```python
from mcp_resilient import CircuitBreakerConfig, ReliabilityConfig, mcp_reliable

config = ReliabilityConfig(
    tool_name="threat_intel",
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        cost_budget=2.00,      # trips even if failures < 5, once $2 is burned
        window_seconds=60,
        cooldown_seconds=30,
    ),
)

@mcp_reliable(config, cost_fn=lambda result: 0.02)  # $ per call, your logic
async def call_threat_intel(ioc: str) -> dict:
    return await mcp_client.call_tool("threat_intel", {"ioc": ioc})
```

## + Fallback chain

Fallback needs the wrapped function to accept `tool_name` and route on it:

```python
from mcp_resilient import FallbackConfig, ReliabilityConfig, mcp_reliable

config = ReliabilityConfig(
    tool_name="primary_search",
    fallback=FallbackConfig(enabled=True, tool_chain=["backup_search"]),
)

@mcp_reliable(config)
async def search(query: str, tool_name: str = "primary_search") -> str:
    return await mcp_client.call_tool(tool_name, {"query": query})
```

## YAML policy files (ops-managed, no code changes)

```yaml
# policy.yaml
tool_name: threat_intel_primary
retry:
  max_attempts: 3
circuit_breaker:
  failure_threshold: 5
  cost_budget: 2.0
fallback:
  enabled: true
  tool_chain: ["threat_intel_backup"]
```

```python
from mcp_resilient import ReliabilityConfig, mcp_reliable

config = ReliabilityConfig.from_yaml("policy.yaml")

@mcp_reliable(config)
async def call_tool(...): ...
```

## Simulate a policy before deploying it

```bash
pip install mcp-resilient[cli]
mcp-resilient simulate policy.yaml --failure-rate 0.4 --calls 100 --cost-per-call 0.02
```

Prints how many calls would be blocked and how much cost would be saved,
without touching a real tool.

## Redis for multi-instance agents

```python
from mcp_resilient.storage.redis_store import RedisStateStore

store = RedisStateStore(url="redis://localhost:6379/0")

@mcp_reliable(config, store=store)
async def call_tool(...): ...
```

## More

Runnable versions of all of the above are in [`examples/`](../examples/).
