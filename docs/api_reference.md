# API Reference

## `mcp_reliable(config, *, store=None, exporter=None, metrics=None, cost_fn=None)`

Decorator. Wraps an async function with retry, circuit breaking, optional
fallback, and observability.

| Param | Type | Default | Purpose |
|---|---|---|---|
| `config` | `ReliabilityConfig` | required | Policy for this tool |
| `store` | `StateStore \| None` | `InMemoryStateStore()` | Circuit breaker state backend |
| `exporter` | `Exporter \| None` | `NoopExporter()` | Where metrics get pushed |
| `metrics` | `MetricsCollector \| None` | module-level default | In-process metrics buffer |
| `cost_fn` | `Callable[[Any], float] \| None` | `None` | Computes $ cost from a call's result |

## `ReliabilityConfig`

```python
ReliabilityConfig(
    tool_name: str,
    retry: RetryConfig = RetryConfig(),
    circuit_breaker: CircuitBreakerConfig = CircuitBreakerConfig(),
    fallback: FallbackConfig = FallbackConfig(),
    observability: ObservabilityConfig = ObservabilityConfig(),
)
```

`ReliabilityConfig.from_yaml(path)` — load from a YAML file (`pip install
mcp-resilient[cli]`).

## `RetryConfig`

| Field | Default | Notes |
|---|---|---|
| `enabled` | `True` | |
| `max_attempts` | `3` | |
| `timeout_seconds` | `10.0` | Per-attempt |
| `backoff` | `BackoffConfig()` | |
| `retry_on` | `(Exception,)` | Tuple of exception types to retry on |

## `BackoffConfig`

| Field | Default | Notes |
|---|---|---|
| `strategy` | `"decorrelated_jitter"` | or `"fixed"`, `"exponential"` |
| `base_delay` | `0.5` | seconds |
| `max_delay` | `30.0` | seconds |
| `multiplier` | `2.0` | used by `"exponential"` |

## `CircuitBreakerConfig`

| Field | Default | Notes |
|---|---|---|
| `enabled` | `True` | |
| `failure_threshold` | `5` | consecutive failures to trip |
| `window_seconds` | `60.0` | rolling window |
| `cooldown_seconds` | `30.0` | OPEN duration before HALF_OPEN |
| `half_open_max_calls` | `1` | probe calls allowed |
| `cost_budget` | `None` | optional $ ceiling per window |

## `FallbackConfig`

| Field | Default | Notes |
|---|---|---|
| `enabled` | `False` | |
| `tool_chain` | `[]` | backup tool names, tried in order |

## `ObservabilityConfig`

| Field | Default | Notes |
|---|---|---|
| `enabled` | `True` | |
| `exporter` | `"none"` | or `"prometheus"`, `"otel"` |
| `log_level` | `"INFO"` | |

## Exceptions

All inherit from `MCPResilientError`.

- `CircuitOpenError(tool_name, retry_after)`
- `RetryExhaustedError(tool_name, attempts, last_error)`
- `FallbackExhaustedError(tool_chain, last_error)`
- `CostBudgetExceededError(tool_name, spent, budget)`

## Storage backends

- `InMemoryStateStore()` — default, single-process.
- `RedisStateStore(url, prefix)` — `pip install mcp-resilient[redis]`, shared
  across instances.
- Implement `StateStore` (`storage/base.py`) for any other backend.

## Observability exporters

- `NoopExporter()` — default.
- `PrometheusExporter()` — `pip install mcp-resilient[prometheus]`.
- `OpenTelemetryExporter()` — `pip install mcp-resilient[otel]`.

## CLI

```bash
mcp-resilient simulate <config.yaml> [--failure-rate 0.3] [--calls 50] [--cost-per-call 0.01]
```
