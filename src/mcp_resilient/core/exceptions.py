from __future__ import annotations


class MCPResilientError(Exception):
    """Base exception for all mcp-resilient errors."""


class CircuitOpenError(MCPResilientError):
    """Raised when a call is blocked because the circuit for a tool is OPEN."""

    def __init__(self, tool_name: str, retry_after: float):
        self.tool_name = tool_name
        self.retry_after = retry_after
        super().__init__(f"Circuit for tool '{tool_name}' is OPEN. Retry after {retry_after:.1f}s.")


class RetryExhaustedError(MCPResilientError):
    """Raised when all retry attempts for a tool call have been exhausted."""

    def __init__(self, tool_name: str, attempts: int, last_error: BaseException):
        self.tool_name = tool_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Tool '{tool_name}' failed after {attempts} attempt(s). Last error: {last_error!r}"
        )


class FallbackExhaustedError(MCPResilientError):
    """Raised when the primary tool and every fallback in the chain have failed."""

    def __init__(self, tool_chain: list[str], last_error: BaseException):
        self.tool_chain = tool_chain
        self.last_error = last_error
        super().__init__(
            f"All tools in fallback chain exhausted: {tool_chain}. Last error: {last_error!r}"
        )


class CostBudgetExceededError(MCPResilientError):
    """Raised when a tool's cumulative cost in the current window exceeds its budget."""

    def __init__(self, tool_name: str, spent: float, budget: float):
        self.tool_name = tool_name
        self.spent = spent
        self.budget = budget
        super().__init__(f"Tool '{tool_name}' exceeded cost budget: ${spent:.4f} / ${budget:.4f}")
