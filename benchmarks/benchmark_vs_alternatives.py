"""Benchmark: quantify what the circuit breaker actually saves.

Runs two scenarios head-to-head over the same synthetic failure trace:
  1. "unguarded" — every call goes straight to the (simulated) upstream.
  2. "mcp-resilient" — calls go through the circuit breaker first.

This produces real numbers for a README/LinkedIn post instead of
unverified claims. Run: `python benchmarks/benchmark_vs_alternatives.py`
"""

from __future__ import annotations

import asyncio
import random

from mcp_resilient.circuit_breaker.breaker import CircuitBreaker
from mcp_resilient.circuit_breaker.state_store import BreakerStateStore
from mcp_resilient.core.config import CircuitBreakerConfig
from mcp_resilient.core.exceptions import CircuitOpenError
from mcp_resilient.storage.memory_store import InMemoryStateStore

CALLS = 500
FAILURE_RATE = 0.35
COST_PER_CALL = 0.02
SEED = 42


def synthetic_trace(n: int, failure_rate: float, seed: int) -> list[bool]:
    rng = random.Random(seed)
    return [rng.random() < failure_rate for _ in range(n)]


async def run_unguarded(trace: list[bool]) -> dict:
    upstream_hits = len(trace)
    cost = sum(COST_PER_CALL for failed in trace if failed)
    return {"upstream_hits": upstream_hits, "wasted_cost_usd": cost}


async def run_guarded(trace: list[bool]) -> dict:
    store = InMemoryStateStore()
    config = CircuitBreakerConfig(failure_threshold=5, cooldown_seconds=1.0, window_seconds=10)
    breaker = CircuitBreaker("benchmark_tool", config, BreakerStateStore(store))

    upstream_hits = 0
    blocked = 0
    cost = 0.0

    for failed in trace:
        try:
            await breaker.before_call()
        except CircuitOpenError:
            blocked += 1
            continue

        upstream_hits += 1
        if failed:
            cost += COST_PER_CALL
            await breaker.record_failure(cost=COST_PER_CALL)
        else:
            await breaker.record_success()

    return {"upstream_hits": upstream_hits, "wasted_cost_usd": cost, "blocked": blocked}


async def main() -> None:
    trace = synthetic_trace(CALLS, FAILURE_RATE, SEED)

    unguarded = await run_unguarded(trace)
    guarded = await run_guarded(trace)

    print(f"Trace: {CALLS} calls, {FAILURE_RATE:.0%} failure rate, seed={SEED}")
    print()
    print(f"{'Scenario':<16} {'Upstream hits':<16} {'Blocked':<10} {'Wasted cost':<12}")
    print(f"{'unguarded':<16} {unguarded['upstream_hits']:<16} {'0':<10} ${unguarded['wasted_cost_usd']:.2f}")
    print(
        f"{'mcp-resilient':<16} {guarded['upstream_hits']:<16} "
        f"{guarded['blocked']:<10} ${guarded['wasted_cost_usd']:.2f}"
    )
    print()
    saved = unguarded["wasted_cost_usd"] - guarded["wasted_cost_usd"]
    pct = (saved / unguarded["wasted_cost_usd"] * 100) if unguarded["wasted_cost_usd"] else 0
    print(f"Cost saved by circuit breaking: ${saved:.2f} ({pct:.1f}%)")
    print(
        "Note: this is a synthetic uniform-random trace, not a production "
        "workload — re-run against real failure logs before quoting numbers publicly."
    )


if __name__ == "__main__":
    asyncio.run(main())
