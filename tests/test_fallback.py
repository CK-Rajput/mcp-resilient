from __future__ import annotations

import pytest

from mcp_resilient.core.config import FallbackConfig
from mcp_resilient.core.exceptions import FallbackExhaustedError
from mcp_resilient.fallback.router import FallbackRouter


async def test_fallback_moves_to_next_tool_on_failure():
    router = FallbackRouter(FallbackConfig(enabled=True, tool_chain=["backup"]))

    async def call(tool: str):
        if tool == "primary":
            raise ConnectionError("down")
        return f"result from {tool}"

    result = await router.run_chain(["primary", "backup"], call)
    assert result == "result from backup"


async def test_fallback_exhausted_raises_with_full_chain():
    router = FallbackRouter(FallbackConfig(enabled=True, tool_chain=["backup"]))

    async def call(tool: str):
        raise ConnectionError(f"{tool} down")

    with pytest.raises(FallbackExhaustedError) as exc_info:
        await router.run_chain(["primary", "backup"], call)

    assert exc_info.value.tool_chain == ["primary", "backup"]


async def test_first_success_short_circuits_remaining_chain():
    calls_made = []

    async def call(tool: str):
        calls_made.append(tool)
        return f"ok:{tool}"

    router = FallbackRouter(FallbackConfig(enabled=True, tool_chain=["backup", "tertiary"]))
    result = await router.run_chain(["primary", "backup", "tertiary"], call)

    assert result == "ok:primary"
    assert calls_made == ["primary"]
