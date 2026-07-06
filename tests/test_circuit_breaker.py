from __future__ import annotations

import asyncio

import pytest

from mcp_resilient.circuit_breaker.breaker import CircuitBreaker
from mcp_resilient.circuit_breaker.state_store import BreakerStateStore
from mcp_resilient.core.config import CircuitBreakerConfig
from mcp_resilient.core.exceptions import CircuitOpenError


async def test_circuit_trips_after_failure_threshold(memory_store):
    config = CircuitBreakerConfig(failure_threshold=3, cooldown_seconds=60)
    breaker = CircuitBreaker("t1", config, BreakerStateStore(memory_store))

    for _ in range(3):
        await breaker.before_call()
        await breaker.record_failure()

    with pytest.raises(CircuitOpenError):
        await breaker.before_call()


async def test_circuit_trips_on_cost_budget_even_below_failure_threshold(memory_store):
    config = CircuitBreakerConfig(failure_threshold=100, cost_budget=0.05)
    breaker = CircuitBreaker("t2", config, BreakerStateStore(memory_store))

    await breaker.before_call()
    await breaker.record_failure(cost=0.03)
    await breaker.before_call()
    await breaker.record_failure(cost=0.03)  # cumulative 0.06 > budget 0.05

    with pytest.raises(CircuitOpenError):
        await breaker.before_call()


async def test_circuit_recovers_through_half_open_after_cooldown(memory_store):
    config = CircuitBreakerConfig(failure_threshold=1, cooldown_seconds=0.1)
    breaker = CircuitBreaker("t3", config, BreakerStateStore(memory_store))

    await breaker.before_call()
    await breaker.record_failure()

    with pytest.raises(CircuitOpenError):
        await breaker.before_call()

    await asyncio.sleep(0.15)

    await breaker.before_call()  # transitions OPEN -> HALF_OPEN, should not raise
    await breaker.record_success()  # closes the circuit
    await breaker.before_call()  # CLOSED, should not raise


async def test_disabled_breaker_never_blocks(memory_store):
    config = CircuitBreakerConfig(enabled=False, failure_threshold=1)
    breaker = CircuitBreaker("t4", config, BreakerStateStore(memory_store))

    for _ in range(10):
        await breaker.before_call()
        await breaker.record_failure()  # should never raise or trip
