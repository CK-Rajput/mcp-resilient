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
    BulkheadConfig,
    HedgedConfig,
    AdaptiveTimeoutConfig,
    RetryBudgetConfig,
    DeduplicationConfig,
    TracingConfig,
)
from mcp_resilient.core.decorator import mcp_reliable
from mcp_resilient.core.exceptions import (
    CircuitOpenError,
    CostBudgetExceededError,
    FallbackExhaustedError,
    MCPResilientError,
    RetryExhaustedError,
    BulkheadFullError,
)
from mcp_resilient.health import check_service_health

__version__ = "0.0.1"

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
    "BulkheadConfig",
    "HedgedConfig",
    "AdaptiveTimeoutConfig",
    "RetryBudgetConfig",
    "DeduplicationConfig",
    "TracingConfig",
    "MCPResilientError",
    "CircuitOpenError",
    "RetryExhaustedError",
    "FallbackExhaustedError",
    "CostBudgetExceededError",
    "BulkheadFullError",
    "check_service_health",
]
