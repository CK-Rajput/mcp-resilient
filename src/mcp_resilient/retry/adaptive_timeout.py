from __future__ import annotations

import time
from collections import deque
from typing import Any

from mcp_resilient.core.config import AdaptiveTimeoutConfig


class AdaptiveTimeoutTracker:
    """Tracks latency history and calculates dynamic timeouts based on percentiles."""

    def __init__(self, config: AdaptiveTimeoutConfig):
        self.config = config
        self.history: deque[float] = deque(maxlen=config.window_size)

    def record_latency(self, latency_seconds: float) -> None:
        self.history.append(latency_seconds)

    def get_timeout(self) -> float:
        if not self.config.enabled or len(self.history) < 5:
            return self.config.max_timeout_seconds

        sorted_latencies = sorted(list(self.history))
        idx = int((self.config.percentile / 100.0) * len(sorted_latencies))
        idx = max(0, min(idx, len(sorted_latencies) - 1))
        percentile_latency = sorted_latencies[idx]

        dynamic_timeout = percentile_latency * 1.5
        return max(
            self.config.min_timeout_seconds,
            min(dynamic_timeout, self.config.max_timeout_seconds),
        )


_adaptive_timeout_trackers: dict[str, AdaptiveTimeoutTracker] = {}


def get_adaptive_timeout_tracker(
    tool_name: str, config: AdaptiveTimeoutConfig
) -> AdaptiveTimeoutTracker:
    if tool_name not in _adaptive_timeout_trackers:
        _adaptive_timeout_trackers[tool_name] = AdaptiveTimeoutTracker(config)
    return _adaptive_timeout_trackers[tool_name]
