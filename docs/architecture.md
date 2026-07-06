# Architecture

## HLD

```
Agent / LLM Client
      |
      v
[ @mcp_reliable decorator ]   <-- this package
      |
      v
MCP Server / Tool (unchanged)
```

Four cooperating modules sit inside the decorator:

1. **Retry Engine** (`retry/`) — per-attempt timeout, configurable backoff
   (fixed / exponential / decorrelated jitter).
2. **Circuit Breaker** (`circuit_breaker/`) — CLOSED / OPEN / HALF_OPEN state
   machine, trips on failure count OR cost budget.
3. **Fallback Router** (`fallback/`) — ordered tool chain, first success wins.
4. **Observability** (`observability/`) — metrics collection + pluggable
   exporters (Prometheus, OpenTelemetry).

State (circuit breaker counters) lives behind a `StateStore` interface
(`storage/`) — in-memory by default, Redis for multi-instance agents.

## LLD

### Call sequence (fallback enabled)

```
wrapper()
  -> breaker.before_call()          # raises CircuitOpenError if OPEN
  -> for tool in [primary, *fallback_chain]:
       -> run_with_retry(attempt, tool)
            -> attempt() -> fn(*args, tool_name=tool, **kwargs)
       -> on success: breaker.record_success() (primary only), break
       -> on failure: breaker.record_failure() (primary only), continue
  -> record CallMetric, export via active exporter
  -> raise FallbackExhaustedError if every hop failed
```

### Circuit breaker state machine

```
CLOSED --(failures >= threshold OR cost >= budget)--> OPEN
OPEN --(cooldown elapsed)--> HALF_OPEN
HALF_OPEN --(probe succeeds)--> CLOSED
HALF_OPEN --(probe fails)--> OPEN
```

### Config schema (Pydantic)

`ReliabilityConfig` → `RetryConfig`, `CircuitBreakerConfig`, `FallbackConfig`,
`ObservabilityConfig`. All validated at construction time (e.g. `max_delay >=
base_delay`), so a bad policy fails at startup, not mid-incident. See
`core/config.py` for the full schema and `docs/quickstart.md` for
`from_yaml()` usage.

## Known v1 limitations (by design, not oversight)

- Circuit breaker guards only the **primary** tool. Per-fallback-hop breaking
  is a natural v2 extension — tracked as a roadmap item, not implemented yet
  because it needs per-hop state keys and changes the cost-budget semantics.
- `FallbackRouter` assumes the wrapped function can route on a `tool_name`
  kwarg. This keeps the router decoupled from any specific MCP client shape,
  but means fallback requires that small convention in your function
  signature (see `examples/fallback_chain_demo.py`).
