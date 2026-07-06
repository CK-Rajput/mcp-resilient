from __future__ import annotations

import functools
import time
from typing import Any, Awaitable, Callable, TypeVar

from mcp_resilient.circuit_breaker.breaker import CircuitBreaker
from mcp_resilient.circuit_breaker.state_store import BreakerStateStore
from mcp_resilient.core.config import ReliabilityConfig
from mcp_resilient.core.exceptions import (
    CircuitOpenError,
    FallbackExhaustedError,
    RetryExhaustedError,
)
from mcp_resilient.observability.exporters import Exporter, NoopExporter
from mcp_resilient.observability.logger import get_logger
from mcp_resilient.observability.metrics import CallMetric, MetricsCollector, Timer
from mcp_resilient.retry.engine import run_with_retry
from mcp_resilient.storage.base import StateStore
from mcp_resilient.storage.memory_store import InMemoryStateStore

# Enterprise features imports
from mcp_resilient.bulkhead.pattern import Bulkhead
from mcp_resilient.retry.hedged import run_with_hedges
from mcp_resilient.retry.adaptive_timeout import get_adaptive_timeout_tracker
from mcp_resilient.retry.budget import get_retry_budget
from mcp_resilient.deduplication.dedup import get_deduplicator
from mcp_resilient.observability.tracing import trace_call

T = TypeVar("T")

_default_metrics = MetricsCollector()


def mcp_reliable(
    config_or_fn: ReliabilityConfig | Callable[..., Awaitable[Any]] | None = None,
    *,
    store: StateStore | None = None,
    exporter: Exporter | None = None,
    metrics: MetricsCollector | None = None,
    cost_fn: Callable[[Any], float] | None = None,
    **kwargs: Any,
):
    """Decorator that wraps an async MCP tool call with retry, circuit
    breaking, optional fallback routing, and observability — no changes
    to the underlying MCP client or protocol required.

    Basic usage:
        config = ReliabilityConfig(tool_name="threat_intel_lookup")

        @mcp_reliable(config)
        async def call_threat_intel(ioc: str):
            return await mcp_client.call_tool("threat_intel_lookup", {"ioc": ioc})

    Direct kwargs usage (automatic config creation):
        @mcp_reliable(retry=RetryConfig(max_attempts=3))
        async def call_threat_intel(ioc: str):
            return await mcp_client.call_tool("threat_intel_lookup", {"ioc": ioc})

    No-parentheses usage (defaults for retry, circuit breaker, etc.):
        @mcp_reliable
        async def call_threat_intel(ioc: str):
            return await mcp_client.call_tool("threat_intel_lookup", {"ioc": ioc})
    """
    backend = store or InMemoryStateStore()
    active_exporter = exporter or NoopExporter()
    active_metrics = metrics or _default_metrics

    def _wrap_function(
        config: ReliabilityConfig, fn: Callable[..., Awaitable[T]]
    ) -> Callable[..., Awaitable[T]]:
        breaker = CircuitBreaker(config.tool_name, config.circuit_breaker, BreakerStateStore(backend))
        logger = get_logger(level=config.observability.log_level)

        bulkhead = Bulkhead(config.tool_name, config.bulkhead)
        timeout_tracker = get_adaptive_timeout_tracker(config.tool_name, config.adaptive_timeout)
        retry_budget = get_retry_budget(config.tool_name, config.retry_budget)
        deduplicator = get_deduplicator(config.tool_name, config.deduplication)

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs_inner: Any) -> T:
            dedup_key = deduplicator.generate_key(args, kwargs_inner)

            async def execute_pipeline() -> T:
                async with trace_call(config.tool_name, config.tracing):
                    async def run_under_bulkhead() -> T:
                        await breaker.before_call()

                        chain = [config.tool_name]
                        if config.fallback.enabled:
                            chain += config.fallback.tool_chain

                        status = "success"
                        cost = 0.0
                        total_retries = 0
                        last_error: BaseException | None = None
                        result: Any = None

                        with Timer() as timer:
                            # Record initial call in retry budget
                            retry_budget.record_call()

                            for idx, tool in enumerate(chain):

                                async def attempt(_tool: str = tool) -> T:
                                    call_kwargs = (
                                        {**kwargs_inner, "tool_name": _tool} if config.fallback.enabled else kwargs_inner
                                    )
                                    if config.hedged.enabled:
                                        return await run_with_hedges(lambda: fn(*args, **call_kwargs), config.hedged)
                                    return await fn(*args, **call_kwargs)

                                try:
                                    current_retry_config = config.retry
                                    if config.adaptive_timeout.enabled:
                                        adaptive_timeout = timeout_tracker.get_timeout()
                                        current_retry_config = config.retry.model_copy(
                                            update={"timeout_seconds": adaptive_timeout}
                                        )

                                    if config.retry.enabled:
                                        outcome = await run_with_retry(
                                            attempt,
                                            current_retry_config,
                                            tool,
                                            retry_budget=retry_budget,
                                        )
                                        result = outcome.result
                                        total_retries += outcome.attempts - 1
                                    else:
                                        result = await attempt()

                                    if config.adaptive_timeout.enabled:
                                        timeout_tracker.record_latency(timer.elapsed_ms / 1000.0)

                                    if cost_fn:
                                        cost += cost_fn(result)
                                    if idx == 0:
                                        await breaker.record_success()
                                    status = "success" if idx == 0 else "fallback"
                                    last_error = None
                                    break

                                except CircuitOpenError:
                                    raise
                                except Exception as exc:  # noqa: BLE001
                                    last_error = exc
                                    if isinstance(exc, RetryExhaustedError):
                                        total_retries += exc.attempts - 1
                                    if idx == 0:
                                        await breaker.record_failure(cost=cost)
                                    logger.warning("tool=%s attempt failed: %r", tool, exc)
                                    continue

                        final_status = status if last_error is None else "failure"
                        metric = CallMetric(
                            tool_name=config.tool_name,
                            timestamp=timer._start,
                            latency_ms=timer.elapsed_ms,
                            status=final_status,
                            cost_usd=cost,
                            retry_count=total_retries,
                        )
                        active_metrics.record(metric)
                        if config.observability.enabled:
                            active_exporter.export(metric)

                        if last_error is not None:
                            if len(chain) > 1:
                                raise FallbackExhaustedError(chain, last_error)
                            raise last_error

                        return result

                    return await bulkhead.execute(run_under_bulkhead)

            return await deduplicator.execute(dedup_key, execute_pipeline)

        return wrapper

    # Case 1: Decorated directly as `@mcp_reliable` without parentheses
    if callable(config_or_fn) and not isinstance(config_or_fn, ReliabilityConfig):
        fn = config_or_fn
        config = ReliabilityConfig(tool_name=fn.__name__)
        return _wrap_function(config, fn)

    # Standard / kwargs usage
    config = config_or_fn

    if config is None:
        tool_name = kwargs.pop("tool_name", "default_tool")
        
        valid_fields = {
            "retry", "circuit_breaker", "fallback", "observability", "rate_limit", "auth",
            "bulkhead", "hedged", "adaptive_timeout", "retry_budget", "deduplication", "tracing"
        }
        invalid_keys = set(kwargs.keys()) - valid_fields
        if invalid_keys:
            raise TypeError(
                f"mcp_reliable() received invalid keyword arguments: {list(invalid_keys)}. "
                f"Valid config options are: {list(valid_fields)}, or pass a ReliabilityConfig object."
            )
            
        config = ReliabilityConfig(tool_name=tool_name, **kwargs)
        
    elif not isinstance(config, ReliabilityConfig):
        raise TypeError(
            "First argument to mcp_reliable() must be a ReliabilityConfig object, "
            "a decorated function, or keyword arguments. "
            f"Received: {type(config).__name__}"
        )
    else:
        if kwargs:
            raise TypeError(
                "Cannot pass both a ReliabilityConfig object and direct keyword arguments to mcp_reliable()."
            )

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        if config.tool_name == "default_tool":
            config.tool_name = fn.__name__
        return _wrap_function(config, fn)

    return decorator
