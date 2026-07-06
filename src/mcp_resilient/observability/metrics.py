from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CallMetric:
    tool_name: str
    timestamp: float
    latency_ms: float
    status: str  # "success" | "failure" | "fallback" | "circuit_open"
    cost_usd: float = 0.0
    retry_count: int = 0


class MetricsCollector:
    """In-process metrics buffer. Drain via an exporter (Prometheus/OTel)
    for dashboards, or read `.summary()` directly for quick diagnostics
    and tests.
    """

    def __init__(self) -> None:
        self._records: list[CallMetric] = []

    def record(self, metric: CallMetric) -> None:
        self._records.append(metric)

    def all(self) -> list[CallMetric]:
        return list(self._records)

    def summary(self, tool_name: str | None = None) -> dict:
        records = [r for r in self._records if tool_name is None or r.tool_name == tool_name]
        if not records:
            return {"count": 0}
        successes = [r for r in records if r.status == "success"]
        return {
            "count": len(records),
            "success_rate": len(successes) / len(records),
            "avg_latency_ms": sum(r.latency_ms for r in records) / len(records),
            "total_cost_usd": sum(r.cost_usd for r in records),
            "total_retries": sum(r.retry_count for r in records),
        }


class Timer:
    """Context helper: `with Timer() as t: ...` then read `t.elapsed_ms`."""

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        self.elapsed_ms = 0.0
        return self

    def __exit__(self, *exc: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
