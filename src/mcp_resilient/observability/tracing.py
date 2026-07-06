from __future__ import annotations

import contextlib
from typing import AsyncGenerator

from mcp_resilient.core.config import TracingConfig


@contextlib.asynccontextmanager
async def trace_call(tool_name: str, config: TracingConfig) -> AsyncGenerator[None, None]:
    if not config.enabled:
        yield
        return

    try:
        from opentelemetry import trace
        tracer = trace.get_tracer(config.tracer_name)
    except ImportError:
        yield
        return

    with tracer.start_as_current_span(f"mcp_reliable:{tool_name}") as span:
        span.set_attribute("mcp.tool_name", tool_name)
        try:
            yield
            span.set_attribute("mcp.status", "success")
        except Exception as exc:
            span.set_attribute("mcp.status", "error")
            span.record_exception(exc)
            raise
