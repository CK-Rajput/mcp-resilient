from __future__ import annotations

import time
from collections import deque
from typing import Any

from mcp_resilient.core.config import RetryBudgetConfig


class RetryBudget:
    """Limits retries within a sliding window to prevent retry storms."""

    def __init__(self, config: RetryBudgetConfig):
        self.config = config
        self.history: deque[tuple[float, str]] = deque()

    def _clean_old_records(self, now: float) -> None:
        cutoff = now - self.config.window_seconds
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()

    def record_call(self) -> None:
        now = time.time()
        self._clean_old_records(now)
        self.history.append((now, "call"))

    def can_retry(self) -> bool:
        if not self.config.enabled:
            return True

        now = time.time()
        self._clean_old_records(now)

        total_calls = sum(1 for _, t in self.history if t == "call")
        total_retries = sum(1 for _, t in self.history if t == "retry")

        if total_calls < self.config.min_requests:
            return True

        current_ratio = total_retries / total_calls
        return current_ratio < self.config.ratio

    def record_retry(self) -> None:
        now = time.time()
        self._clean_old_records(now)
        self.history.append((now, "retry"))


_retry_budgets: dict[str, RetryBudget] = {}


def get_retry_budget(tool_name: str, config: RetryBudgetConfig) -> RetryBudget:
    if tool_name not in _retry_budgets:
        _retry_budgets[tool_name] = RetryBudget(config)
    return _retry_budgets[tool_name]
