from __future__ import annotations

import asyncio
import time
import pytest
from mcp_resilient import (
    mcp_reliable,
    ReliabilityConfig,
    BulkheadConfig,
    HedgedConfig,
    AdaptiveTimeoutConfig,
    RetryBudgetConfig,
    DeduplicationConfig,
    TracingConfig,
    BulkheadFullError,
    RetryExhaustedError,
    check_service_health,
)
from mcp_resilient.storage.memory_store import InMemoryStateStore

# 1. Test Bulkhead Pattern
async def test_bulkhead_concurrency_limit():
    config = ReliabilityConfig(
        tool_name="bulkhead_tool",
        bulkhead=BulkheadConfig(enabled=True, max_concurrent_calls=2, max_queue_time_seconds=0.1),
    )

    running_calls = 0
    max_running_observed = 0

    @mcp_reliable(config)
    async def run_call():
        nonlocal running_calls, max_running_observed
        running_calls += 1
        max_running_observed = max(max_running_observed, running_calls)
        await asyncio.sleep(0.2)
        running_calls -= 1
        return "ok"

    # Run 3 concurrent calls. The 3rd should fail since limit is 2 and wait time is 0.1s while tasks take 0.2s
    tasks = [run_call() for _ in range(3)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = [r for r in results if r == "ok"]
    failures = [r for r in results if isinstance(r, BulkheadFullError)]

    assert len(successes) == 2
    assert len(failures) == 1
    assert max_running_observed <= 2


# 2. Test Hedged Requests
async def test_hedged_requests_fastest():
    config = ReliabilityConfig(
        tool_name="hedged_tool",
        hedged=HedgedConfig(enabled=True, hedges=2, delay_seconds=0.05),
        retry=dict(enabled=False),
    )

    call_index = 0

    @mcp_reliable(config)
    async def slow_then_fast_tool():
        nonlocal call_index
        idx = call_index
        call_index += 1
        if idx == 0:
            # First attempt hangs/is slow
            await asyncio.sleep(0.3)
            return "slow"
        else:
            # Second attempt is fast
            return "fast"

    result = await slow_then_fast_tool()
    # The hedge request should trigger after 0.05s and return "fast" first, cancelling the slow first request
    assert result == "fast"


# 3. Test Adaptive Timeout
async def test_adaptive_timeout():
    config = ReliabilityConfig(
        tool_name="adaptive_tool",
        adaptive_timeout=AdaptiveTimeoutConfig(
            enabled=True, percentile=90, min_timeout_seconds=0.05, max_timeout_seconds=0.5
        ),
    )

    call_count = 0

    @mcp_reliable(config)
    async def flaky_timeout_tool():
        nonlocal call_count
        call_count += 1
        if call_count <= 5:
            # Warm up with fast responses to establish a low dynamic timeout
            return "fast"
        else:
            # This should exceed the low dynamic timeout and raise TimeoutError
            await asyncio.sleep(0.2)
            return "slow"

    # Execute 5 times to warm up the history
    for _ in range(5):
        await flaky_timeout_tool()

    # The 6th call should fail due to adaptive timeout
    with pytest.raises(RetryExhaustedError):
        await flaky_timeout_tool()


# 4. Test Distributed Circuit Breaker (wall-clock sync)
async def test_circuit_breaker_wall_clock():
    from mcp_resilient.circuit_breaker.state_store import BreakerStateStore
    store = InMemoryStateStore()
    breaker_store = BreakerStateStore(store)

    # Initial state should populate window_started_at using time.time()
    state = await breaker_store.get_state("test_tool")
    assert state.window_started_at > 0
    # Difference should be minimal compared to current time.time()
    assert abs(state.window_started_at - time.time()) < 5.0


# 5. Test Retry Budget
async def test_retry_budget_limit():
    # Only allow 10% retries after 5 requests
    config = ReliabilityConfig(
        tool_name="budget_tool",
        retry=dict(max_attempts=3),
        retry_budget=RetryBudgetConfig(enabled=True, ratio=0.1, min_requests=5, window_seconds=10),
    )

    should_fail = False

    @mcp_reliable(config)
    async def flaky_budget_tool():
        if should_fail:
            raise ConnectionError("downstream failure")
        return "ok"

    # Make 5 successful requests to build total_calls to 5
    for _ in range(5):
        await flaky_budget_tool()

    # Trigger failure. It will retry once, but then fail because retry ratio would exceed 10%
    should_fail = True
    with pytest.raises(RetryExhaustedError) as exc_info:
        await flaky_budget_tool()

    assert "Retry budget exhausted" in str(exc_info.value.last_error)


# 6. Test Request Deduplication
async def test_request_deduplication():
    config = ReliabilityConfig(
        tool_name="dedup_tool",
        deduplication=DeduplicationConfig(enabled=True),
        retry=dict(enabled=False),
    )

    execution_count = 0

    @mcp_reliable(config)
    async def slow_identity_tool(val: str):
        nonlocal execution_count
        execution_count += 1
        await asyncio.sleep(0.1)
        return f"result-{val}"

    # Fire 3 concurrent calls with the same argument
    tasks = [slow_identity_tool("hello") for _ in range(3)]
    results = await asyncio.gather(*tasks)

    assert results == ["result-hello", "result-hello", "result-hello"]
    # Coalesced: function should only have run once!
    assert execution_count == 1


# 7. Test OpenTelemetry Auto Tracing
async def test_opentelemetry_tracing():
    config = ReliabilityConfig(
        tool_name="tracing_tool",
        tracing=TracingConfig(enabled=True),
        retry=dict(enabled=False),
    )

    @mcp_reliable(config)
    async def traced_tool():
        return "trace"

    res = await traced_tool()
    assert res == "trace"


# 8. Test Kubernetes Health Check
async def test_k8s_health_endpoint():
    store = InMemoryStateStore()
    config_healthy = ReliabilityConfig(tool_name="healthy_cb")
    config_unhealthy = ReliabilityConfig(tool_name="unhealthy_cb")

    # Force the circuit open for unhealthy_cb in state store
    from mcp_resilient.circuit_breaker.state_store import BreakerStateStore, BreakerState
    breaker_store = BreakerStateStore(store)
    await breaker_store._save("unhealthy_cb", BreakerState(status="open"))

    # Test healthy check (only healthy config checked)
    health = await check_service_health([config_healthy], store)
    assert health["status"] == "healthy"
    assert health["code"] == 200

    # Test unhealthy check (including tripped cb config)
    health_mixed = await check_service_health([config_healthy, config_unhealthy], store)
    assert health_mixed["status"] == "unhealthy"
    assert health_mixed["code"] == 503
    assert health_mixed["tools"]["unhealthy_cb"]["status"] == "unhealthy"

    # Test degraded check (circuit is half_open)
    await breaker_store._save("unhealthy_cb", BreakerState(status="half_open"))
    health_half = await check_service_health([config_healthy, config_unhealthy], store)
    assert health_half["status"] == "unhealthy"
    assert health_half["tools"]["unhealthy_cb"]["status"] == "degraded"

    # Test dict config input
    dict_config = {"tool_name": "dict_cb", "circuit_breaker": {"enabled": True}}
    health_dict = await check_service_health([dict_config], store)
    assert health_dict["status"] == "healthy"

    # Test missing tool_name raising ValueError
    with pytest.raises(ValueError) as exc_info:
        await check_service_health([{"circuit_breaker": {"enabled": True}}], store)
    assert "Invalid configuration dictionary: 'tool_name' is missing." in str(exc_info.value)

    # Test state store read failures (handling exceptions fail-safely)
    from mcp_resilient.storage.base import StateStore
    class FailingStateStore(StateStore):
        async def get(self, key: str):
            raise ConnectionError("Redis is down")
        async def set(self, key: str, value: dict[str, Any]) -> None:
            pass
        async def delete(self, key: str) -> None:
            pass

    failing_store = FailingStateStore()
    health_fail = await check_service_health([config_healthy], failing_store)
    assert health_fail["status"] == "unhealthy"
    assert health_fail["code"] == 503
    assert health_fail["tools"]["healthy_cb"]["circuit"] == "error"
    assert "Redis is down" in health_fail["tools"]["healthy_cb"]["error"]

    # Test health check timeout (timeout guard)
    class HangingStateStore(StateStore):
        async def get(self, key: str):
            await asyncio.sleep(0.5)
            return None
        async def set(self, key: str, value: dict[str, Any]) -> None:
            pass
        async def delete(self, key: str) -> None:
            pass

    hanging_store = HangingStateStore()
    health_timeout = await check_service_health([config_healthy], hanging_store, timeout=0.1)
    assert health_timeout["status"] == "unhealthy"
    assert health_timeout["code"] == 503
    assert "timed out" in health_timeout["error"]
