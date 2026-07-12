"""mcp-resilient: production-grade reliability layer for MCP tool calls.

Adaptive retry, cost-aware circuit breaking, ordered fallback chains,
and pluggable observability — as a drop-in decorator around any
existing MCP client. No protocol changes, no rebuild.
"""

from mcp_resilient.core.config import (
    AuthConfig,
    BackoffConfig,
    CircuitBreakerConfig,
    FallbackConfig,
    ObservabilityConfig,
    RateLimitConfig,
    ReliabilityConfig,
    RetryConfig,
)
from mcp_resilient.core.decorator import mcp_reliable
from mcp_resilient.core.exceptions import (
    CircuitOpenError,
    CostBudgetExceededError,
    FallbackExhaustedError,
    MCPResilientError,
    RetryExhaustedError,
)

__version__ = "0.1.0"

__all__ = [
    "mcp_reliable",
    "ReliabilityConfig",
    "RetryConfig",
    "BackoffConfig",
    "CircuitBreakerConfig",
    "FallbackConfig",
    "ObservabilityConfig",
    "RateLimitConfig",
    "AuthConfig",
    "MCPResilientError",
    "CircuitOpenError",
    "RetryExhaustedError",
    "FallbackExhaustedError",
    "CostBudgetExceededError",
]
