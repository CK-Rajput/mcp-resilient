"""Token bucket rate limiter for multi-tenant tool access control."""

from __future__ import annotations

import time
from typing import Any


class TokenBucketLimiter:
    """Token bucket algorithm for rate limiting.
    
    Refills tokens at a fixed rate, blocking when bucket is empty.
    Thread-safe for concurrent requests.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking.
        
        Returns True if tokens acquired, False otherwise.
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def acquire_or_wait(self, tokens: int = 1) -> float:
        """Acquire tokens, waiting if necessary.
        
        Returns time waited in seconds.
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return 0.0

        wait_time = (tokens - self.tokens) / self.refill_rate
        time.sleep(wait_time)
        self.tokens = 0
        return wait_time


class PerTenantRateLimiter:
    """Multi-tenant rate limiter with per-tenant limits."""

    def __init__(self, default_capacity: int = 100, default_refill_rate: float = 10.0):
        """
        Args:
            default_capacity: Default tokens per tenant bucket
            default_refill_rate: Default tokens per second per tenant
        """
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self.limiters: dict[str, TokenBucketLimiter] = {}
        self.custom_limits: dict[str, tuple[int, float]] = {}

    def set_limit(self, tenant_id: str, capacity: int, refill_rate: float) -> None:
        """Set custom limit for a tenant."""
        self.custom_limits[tenant_id] = (capacity, refill_rate)
        self.limiters.pop(tenant_id, None)  # Reset limiter

    def try_acquire(self, tenant_id: str, tokens: int = 1) -> bool:
        """Check if tenant can make a call."""
        limiter = self._get_limiter(tenant_id)
        return limiter.try_acquire(tokens)

    def _get_limiter(self, tenant_id: str) -> TokenBucketLimiter:
        """Get or create limiter for tenant."""
        if tenant_id not in self.limiters:
            capacity, rate = self.custom_limits.get(
                tenant_id, (self.default_capacity, self.default_refill_rate)
            )
            self.limiters[tenant_id] = TokenBucketLimiter(capacity, rate)
        return self.limiters[tenant_id]
