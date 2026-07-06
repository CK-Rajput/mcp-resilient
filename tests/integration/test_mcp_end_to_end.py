from __future__ import annotations

from mcp_resilient import ReliabilityConfig, RetryConfig, mcp_reliable
from mcp_resilient.core.config import BackoffConfig, CircuitBreakerConfig, FallbackConfig
from mcp_resilient.observability.metrics import MetricsCollector


async def test_full_pipeline_retry_then_fallback_then_metrics():
    metrics = MetricsCollector()
    attempts = {"primary": 0, "backup": 0}

    config = ReliabilityConfig(
        tool_name="primary",
        retry=RetryConfig(max_attempts=2, backoff=BackoffConfig(base_delay=0.01, max_delay=0.02)),
        circuit_breaker=CircuitBreakerConfig(failure_threshold=10),
        fallback=FallbackConfig(enabled=True, tool_chain=["backup"]),
    )

    @mcp_reliable(config, metrics=metrics)
    async def call(tool_name: str = "primary"):
        attempts[tool_name] += 1
        if tool_name == "primary":
            raise ConnectionError("primary down")
        return "backup-result"

    result = await call()

    assert result == "backup-result"
    assert attempts["primary"] == 2  # retried once on primary before giving up
    assert attempts["backup"] == 1

    summary = metrics.summary("primary")
    assert summary["count"] == 1
    assert summary["total_retries"] >= 1


async def test_full_pipeline_success_on_first_try_records_clean_metric():
    metrics = MetricsCollector()

    config = ReliabilityConfig(tool_name="healthy_tool")

    @mcp_reliable(config, metrics=metrics)
    async def call():
        return "ok"

    result = await call()

    assert result == "ok"
    summary = metrics.summary("healthy_tool")
    assert summary["count"] == 1
    assert summary["success_rate"] == 1.0
    assert summary["total_retries"] == 0


async def test_full_pipeline_circuit_opens_and_blocks_before_call():
    from mcp_resilient.core.exceptions import CircuitOpenError

    metrics = MetricsCollector()
    config = ReliabilityConfig(
        tool_name="always_fails",
        retry=RetryConfig(max_attempts=1),
        circuit_breaker=CircuitBreakerConfig(failure_threshold=1, cooldown_seconds=60),
    )

    @mcp_reliable(config, metrics=metrics)
    async def call():
        raise ConnectionError("nope")

    try:
        await call()
    except Exception:
        pass  # first call trips the breaker

    import pytest

    with pytest.raises(CircuitOpenError):
        await call()
