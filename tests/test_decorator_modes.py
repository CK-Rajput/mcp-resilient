from __future__ import annotations

import pytest
from mcp_resilient import mcp_reliable, RetryConfig, ReliabilityConfig
from mcp_resilient.core.exceptions import RetryExhaustedError

async def test_decorator_no_parentheses():
    call_count = 0

    @mcp_reliable
    async def my_simple_tool():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("transient")
        return "success"

    # Default retry is enabled (max_attempts = 3)
    result = await my_simple_tool()
    assert result == "success"
    assert call_count == 2


async def test_decorator_direct_kwargs():
    call_count = 0

    # Configure only 2 attempts via direct kwargs
    @mcp_reliable(retry=RetryConfig(max_attempts=2))
    async def my_limited_tool():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("transient")

    with pytest.raises(RetryExhaustedError):
        await my_limited_tool()

    assert call_count == 2


def test_decorator_invalid_kwargs():
    with pytest.raises(TypeError) as exc_info:
        @mcp_reliable(invalid_setting="some_val")
        async def my_tool():
            pass
            
    assert "received invalid keyword arguments: ['invalid_setting']" in str(exc_info.value)
    assert "Valid config options are" in str(exc_info.value)


def test_decorator_invalid_positional_arg():
    with pytest.raises(TypeError) as exc_info:
        mcp_reliable("not_a_config_object")  # type: ignore
            
    assert "must be a ReliabilityConfig object, a decorated function, or keyword arguments" in str(exc_info.value)
