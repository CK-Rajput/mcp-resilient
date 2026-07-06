from __future__ import annotations

from typing import Any, Awaitable, Callable

from mcp_resilient.core.config import FallbackConfig
from mcp_resilient.core.exceptions import FallbackExhaustedError


class FallbackRouter:
    """Tries an ordered chain of tool names until one succeeds.

    `call` is a single callable that takes a tool name and dispatches to
    the right underlying tool — this keeps the router decoupled from any
    specific MCP client shape. See `core.decorator.mcp_reliable` for how
    the wrapped function is expected to use its `tool_name` argument.
    """

    def __init__(self, config: FallbackConfig):
        self.config = config

    async def run_chain(
        self,
        chain: list[str],
        call: Callable[[str], Awaitable[Any]],
    ) -> Any:
        last_error: BaseException | None = None

        for tool in chain:
            try:
                return await call(tool)
            except Exception as exc:  # noqa: BLE001 — deliberately broad, this is a router
                last_error = exc
                continue

        assert last_error is not None
        raise FallbackExhaustedError(chain, last_error)
