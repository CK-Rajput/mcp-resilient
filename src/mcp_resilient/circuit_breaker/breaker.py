from __future__ import annotations

import time
from enum import Enum

from mcp_resilient.circuit_breaker.state_store import BreakerStateStore
from mcp_resilient.core.config import CircuitBreakerConfig
from mcp_resilient.core.exceptions import CircuitOpenError


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-tool circuit breaker.

    Trips on EITHER failure-count threshold OR cost-budget breach within
    a rolling window — whichever fires first. Cost-aware tripping is the
    key differentiator vs. plain circuit breakers: a tool can look
    "healthy" by failure count alone while still burning through an API
    budget on retries. This breaker catches that case too.
    """

    def __init__(self, tool_name: str, config: CircuitBreakerConfig, store: BreakerStateStore):
        self.tool_name = tool_name
        self.config = config
        self.store = store

    async def before_call(self) -> None:
        if not self.config.enabled:
            return

        state = await self.store.get_state(self.tool_name)

        if state.status == CircuitState.OPEN.value:
            elapsed = time.time() - state.opened_at
            if elapsed < self.config.cooldown_seconds:
                raise CircuitOpenError(self.tool_name, self.config.cooldown_seconds - elapsed)
            await self.store.transition(self.tool_name, CircuitState.HALF_OPEN.value)
            await self.store.mark_half_open_attempt(self.tool_name)
            return

        if state.status == CircuitState.HALF_OPEN.value:
            if state.half_open_calls >= self.config.half_open_max_calls:
                raise CircuitOpenError(self.tool_name, self.config.cooldown_seconds)
            await self.store.mark_half_open_attempt(self.tool_name)

    async def record_success(self) -> None:
        if not self.config.enabled:
            return
        await self.store.record_success(self.tool_name, self.config)

    async def record_failure(self, cost: float = 0.0) -> None:
        if not self.config.enabled:
            return
        await self.store.record_failure(self.tool_name, self.config, cost)
