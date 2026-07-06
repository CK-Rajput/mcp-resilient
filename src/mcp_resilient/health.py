from __future__ import annotations

import asyncio
import logging
from typing import Any, TypedDict

from mcp_resilient.circuit_breaker.state_store import BreakerStateStore
from mcp_resilient.core.config import ReliabilityConfig
from mcp_resilient.storage.base import StateStore

logger = logging.getLogger("mcp-resilient-health")


class CircuitBreakerDict(TypedDict, total=False):
    enabled: bool
    failure_threshold: int
    window_seconds: float
    cooldown_seconds: float
    cost_budget: float | None


class ReliabilityConfigDict(TypedDict, total=False):
    tool_name: str
    circuit_breaker: CircuitBreakerDict


async def check_service_health(
    configs: list[ReliabilityConfig | ReliabilityConfigDict],
    store: StateStore,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Evaluates the health status of wrapped MCP tools.

    Checks the circuit breaker status of each tool using the StateStore.
    If any enabled circuit breaker is in the 'open' state, or if the checks
    exceed the timeout, returns a 503 unhealthy status for Kubernetes probes.
    """
    if store is None:
        raise ValueError("StateStore 'store' parameter is required for check_service_health.")

    async def _run_health_checks() -> dict[str, Any]:
        breaker_store = BreakerStateStore(store)
        details = {}
        is_healthy = True

        for config in configs:
            if isinstance(config, dict):
                tool_name = config.get("tool_name")
                if not tool_name:
                    raise ValueError("Invalid configuration dictionary: 'tool_name' is missing.")
                cb_config = config.get("circuit_breaker", {})
                cb_enabled = (
                    cb_config.get("enabled", True)
                    if isinstance(cb_config, dict)
                    else getattr(cb_config, "enabled", True)
                )
            elif isinstance(config, ReliabilityConfig):
                tool_name = config.tool_name
                cb_enabled = config.circuit_breaker.enabled
            else:
                raise ValueError(
                    f"Invalid config type: expected ReliabilityConfig or dict, got {type(config).__name__}"
                )

            if not cb_enabled:
                details[tool_name] = {"status": "healthy", "circuit": "disabled"}
                continue

            try:
                state = await breaker_store.get_state(tool_name)
                status = state.status
                status_str = status.value if hasattr(status, "value") else str(status)
                failure_count = state.failure_count
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to retrieve circuit breaker state for tool '%s': %r", tool_name, exc)
                is_healthy = False
                details[tool_name] = {
                    "status": "unhealthy",
                    "circuit": "error",
                    "error": str(exc),
                }
                continue

            # Evaluate the circuit breaker state and map to tool health status:
            # - If status is 'open': The circuit is tripped due to errors. The tool is UNHEALTHY.
            # - If status is 'half_open': The circuit is probing for recovery. The tool is DEGRADED.
            # - Otherwise (e.g. 'closed'): The circuit is operational. The tool is HEALTHY.
            if status_str == "open":
                is_healthy = False
                details[tool_name] = {
                    "status": "unhealthy",
                    "circuit": status_str,
                    "failure_count": failure_count,
                }
            elif status_str == "half_open":
                is_healthy = False  # Degraded tools are treated as unhealthy for K8s readiness probes to prevent traffic routing
                details[tool_name] = {
                    "status": "degraded",
                    "circuit": status_str,
                    "failure_count": failure_count,
                }
            else:
                details[tool_name] = {
                    "status": "healthy",
                    "circuit": status_str,
                    "failure_count": failure_count,
                }

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "code": 200 if is_healthy else 503,
            "tools": details,
        }

    try:
        return await asyncio.wait_for(_run_health_checks(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error("Service health check timed out after %.2f seconds.", timeout)
        return {
            "status": "unhealthy",
            "code": 503,
            "error": f"Health check timed out after {timeout:.2f}s reading from state store",
            "tools": {},
        }
