from __future__ import annotations

from typing import Any, Protocol


class MCPClientProtocol(Protocol):
    """Structural type for any MCP client (official SDK or custom).

    mcp-resilient only needs a `call_tool` coroutine — it does not
    require a specific MCP SDK version or transport.
    """

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any: ...


async def call_via_client(client: MCPClientProtocol, tool_name: str, **arguments: Any) -> Any:
    """Thin helper for wiring an MCP client into a function decorated with @mcp_reliable."""
    return await client.call_tool(tool_name, arguments)
