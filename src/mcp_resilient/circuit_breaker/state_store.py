from __future__ import annotations

import time
from dataclasses import dataclass, field

from mcp_resilient.core.config import CircuitBreakerConfig
from mcp_resilient.storage.base import StateStore


@dataclass
class BreakerState:
    status: str = "closed"  # closed | open | half_open
    failure_count: int = 0
    cost_spent: float = 0.0
    window_started_at: float = field(default_factory=time.time)
    opened_at: float = 0.0
    half_open_calls: int = 0


class BreakerStateStore:
    """Wraps a generic StateStore (memory/redis) with the transition
    logic specific to circuit breakers: windowed failure counting,
    cost-budget tracking, and CLOSED/OPEN/HALF_OPEN bookkeeping.
    """

    def __init__(self, backend: StateStore):
        self.backend = backend

    def _key(self, tool_name: str) -> str:
        return f"cb:{tool_name}"

    async def get_state(self, tool_name: str) -> BreakerState:
        raw = await self.backend.get(self._key(tool_name))
        if raw is None:
            return BreakerState()
        return BreakerState(**raw)

    async def _save(self, tool_name: str, state: BreakerState) -> None:
        await self.backend.set(self._key(tool_name), state.__dict__)

    async def transition(self, tool_name: str, new_status: str) -> None:
        state = await self.get_state(tool_name)
        state.status = new_status
        if new_status == "half_open":
            state.half_open_calls = 0
        await self._save(tool_name, state)

    async def mark_half_open_attempt(self, tool_name: str) -> None:
        state = await self.get_state(tool_name)
        state.half_open_calls += 1
        await self._save(tool_name, state)

    async def record_success(self, tool_name: str, config: CircuitBreakerConfig) -> None:
        state = await self.get_state(tool_name)
        if state.status == "half_open":
            # A successful probe closes the circuit and resets all counters.
            state = BreakerState()
        else:
            state.failure_count = 0
            state.cost_spent = 0.0
        await self._save(tool_name, state)

    async def record_failure(
        self, tool_name: str, config: CircuitBreakerConfig, cost: float
    ) -> None:
        state = await self.get_state(tool_name)
        now = time.time()

        if now - state.window_started_at > config.window_seconds:
            state.failure_count = 0
            state.cost_spent = 0.0
            state.window_started_at = now

        state.failure_count += 1
        state.cost_spent += cost

        should_trip = state.failure_count >= config.failure_threshold or (
            config.cost_budget is not None and state.cost_spent >= config.cost_budget
        )

        if state.status == "half_open" or should_trip:
            state.status = "open"
            state.opened_at = now

        await self._save(tool_name, state)
