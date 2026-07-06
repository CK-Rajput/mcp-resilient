from __future__ import annotations

import random

from mcp_resilient.core.config import BackoffConfig


def compute_delay(
    config: BackoffConfig, attempt: int, previous_delay: float | None = None
) -> float:
    """Compute delay (seconds) before the next retry attempt.

    `attempt` is the 1-indexed attempt number that just failed.

    Strategies:
    - fixed: always `base_delay`.
    - exponential: `base_delay * multiplier^(attempt-1)`, deterministic.
    - decorrelated_jitter: AWS-style — each delay is a random value between
      base_delay and 3x the previous delay. Smarter than plain exponential
      for shared upstreams: many agents retrying the same flaky tool spread
      out instead of synchronizing into a thundering herd on the same
      backoff schedule.
    """
    if config.strategy == "fixed":
        delay = config.base_delay
    elif config.strategy == "exponential":
        delay = config.base_delay * (config.multiplier ** (attempt - 1))
    elif config.strategy == "decorrelated_jitter":
        prev = previous_delay or config.base_delay
        delay = random.uniform(config.base_delay, prev * 3)
    else:  # pragma: no cover — pydantic Literal already constrains this
        raise ValueError(f"Unknown backoff strategy: {config.strategy}")

    return min(delay, config.max_delay)
