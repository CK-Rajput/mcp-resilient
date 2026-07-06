from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BackoffConfig(BaseModel):
    """Controls delay between retry attempts."""

    strategy: Literal["fixed", "exponential", "decorrelated_jitter"] = "decorrelated_jitter"
    base_delay: float = Field(default=0.5, gt=0, description="Seconds, floor for all strategies.")
    max_delay: float = Field(default=30.0, gt=0, description="Seconds, hard ceiling.")
    multiplier: float = Field(default=2.0, gt=1.0, description="Used by 'exponential' strategy.")

    @field_validator("max_delay")
    @classmethod
    def _max_at_least_base(cls, v: float, info) -> float:
        base = info.data.get("base_delay")
        if base is not None and v < base:
            raise ValueError("max_delay must be >= base_delay")
        return v


class CircuitBreakerConfig(BaseModel):
    """Controls when a tool gets temporarily cut off from traffic."""

    enabled: bool = True
    failure_threshold: int = Field(default=5, ge=1, description="Consecutive failures to trip.")
    window_seconds: float = Field(default=60.0, gt=0, description="Rolling window for counting.")
    cooldown_seconds: float = Field(default=30.0, gt=0, description="Time OPEN before HALF_OPEN.")
    half_open_max_calls: int = Field(
        default=1, ge=1, description="Probe calls allowed in HALF_OPEN."
    )
    cost_budget: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Optional $ budget per window. If cumulative cost of failed calls "
            "crosses this, the circuit trips even if failure_threshold hasn't "
            "been hit yet — catches 'technically healthy but burning budget' tools."
        ),
    )


class RetryConfig(BaseModel):
    """Controls per-call retry behavior."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    enabled: bool = True
    max_attempts: int = Field(default=3, ge=1)
    timeout_seconds: float = Field(default=10.0, gt=0, description="Per-attempt timeout.")
    backoff: BackoffConfig = Field(default_factory=BackoffConfig)
    retry_on: tuple[type[BaseException], ...] = Field(default=(Exception,))


class FallbackConfig(BaseModel):
    """Controls the ordered chain of backup tools tried after the primary fails."""

    enabled: bool = False
    tool_chain: list[str] = Field(
        default_factory=list, description="Backup tool names, tried in order."
    )


class ObservabilityConfig(BaseModel):
    """Controls metrics export and logging verbosity."""

    enabled: bool = True
    exporter: Literal["none", "prometheus", "otel"] = "none"
    log_level: str = "INFO"


class RateLimitConfig(BaseModel):
    """Controls per-tenant rate limiting."""

    enabled: bool = False
    default_capacity: int = Field(
        default=100, ge=1, description="Max tokens per tenant bucket."
    )
    default_refill_rate: float = Field(
        default=10.0, gt=0, description="Tokens per second per tenant."
    )


class AuthConfig(BaseModel):
    """Controls authentication and authorization configuration.
    
    NOTE: AuthConfig serves as a policy declaration. The actual token validation 
    and permission checks are not enforced inline by the @mcp_reliable decorator 
    itself; instead, they must be implemented by the developer in their execution 
    layer using an AuthProvider (see mcp_resilient.auth.provider).
    
    WARNING: This class defines access-control routing policies for resilience 
    and cost limits. It is NOT a compliance, encryption, or cryptographic security 
    layer. Developers in regulated domains (such as healthcare or finance) must 
    ensure that actual data encryption, transport security, and compliance audits 
    are handled by their core platform architecture.
    """

    enabled: bool = False
    provider: Literal["none", "static", "custom"] = "none"
    require_token: bool = Field(default=True, description="Raise error if token missing.")
    token_header: str = Field(default="Authorization", description="Header to read token from.")


class BulkheadConfig(BaseModel):
    """Controls the bulkhead pattern to limit concurrent tool calls."""

    enabled: bool = False
    max_concurrent_calls: int = Field(default=10, ge=1, description="Max concurrent executions allowed.")
    max_queue_time_seconds: float | None = Field(
        default=None, description="Max time to wait in queue before timing out and failing."
    )


class HedgedConfig(BaseModel):
    """Controls hedged requests to reduce tail latency by spawning parallel calls."""

    enabled: bool = False
    hedges: int = Field(default=2, ge=1, description="Number of backup concurrent requests to spawn.")
    delay_seconds: float = Field(default=0.2, gt=0, description="Delay before spawning the next hedge request.")


class AdaptiveTimeoutConfig(BaseModel):
    """Controls dynamic timeouts based on latency histories percentiles."""

    enabled: bool = False
    percentile: float = Field(default=95.0, ge=50.0, le=99.9, description="Target percentile latency.")
    min_timeout_seconds: float = Field(default=0.5, gt=0, description="Min floor timeout.")
    max_timeout_seconds: float = Field(default=30.0, gt=0, description="Max ceiling timeout.")
    window_size: int = Field(default=100, ge=10, description="Size of rolling history window.")


class RetryBudgetConfig(BaseModel):
    """Controls retry budgets to prevent retry storms."""

    enabled: bool = False
    ratio: float = Field(default=0.1, gt=0.0, le=1.0, description="Max retry ratio (e.g. 0.1 for 10% retries).")
    min_requests: int = Field(default=10, ge=1, description="Min requests in window before enforcing budget.")
    window_seconds: float = Field(default=60.0, gt=0, description="Sliding window duration in seconds.")


class DeduplicationConfig(BaseModel):
    """Controls request deduplication (single-flight execution coalescing)."""

    enabled: bool = False


class TracingConfig(BaseModel):
    """Controls OpenTelemetry span auto tracing instrumentation."""

    enabled: bool = False
    tracer_name: str = Field(default="mcp-resilient", description="Name of the tracer.")


class ReliabilityConfig(BaseModel):
    """Top-level config for a single tool wrapped by @mcp_reliable.

    Can be constructed directly in code, or loaded from YAML via
    `ReliabilityConfig.from_yaml(path)` for ops-managed policy files.
    """

    tool_name: str
    retry: RetryConfig = Field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    bulkhead: BulkheadConfig = Field(default_factory=BulkheadConfig)
    hedged: HedgedConfig = Field(default_factory=HedgedConfig)
    adaptive_timeout: AdaptiveTimeoutConfig = Field(default_factory=AdaptiveTimeoutConfig)
    retry_budget: RetryBudgetConfig = Field(default_factory=RetryBudgetConfig)
    deduplication: DeduplicationConfig = Field(default_factory=DeduplicationConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)

    @classmethod
    def from_yaml(cls, path: str) -> "ReliabilityConfig":
        """Load config from a YAML policy file. Requires: pip install mcp-resilient[cli]"""
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise ImportError("pyyaml not installed. Run: pip install mcp-resilient[cli]") from exc

        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
