from __future__ import annotations

from typing import Any, Callable

from mcp_resilient.core.config import ReliabilityConfig
from mcp_resilient.core.decorator import mcp_reliable


def wrap_langchain_tool(tool: Any, config: ReliabilityConfig) -> Any:
    """Wraps a LangChain/LangGraph Tool's async entrypoint with mcp-resilient.

    Works with BaseTool subclasses (`_arun`) and StructuredTool instances
    (`coroutine`) — the two common shapes for async LangChain tools.

    Requires: langchain-core (not a hard dependency of mcp-resilient).
    """
    if getattr(tool, "coroutine", None) is not None:
        original: Callable = tool.coroutine
        tool.coroutine = mcp_reliable(config)(original)
        return tool

    if hasattr(tool, "_arun"):
        original = tool._arun
        tool._arun = mcp_reliable(config)(original)
        return tool

    raise TypeError(
        "Unsupported tool type — expected a LangChain Tool with a `coroutine` or `_arun` attribute."
    )
