from __future__ import annotations

from typing import Protocol

from mcp_resilient.observability.metrics import CallMetric


class Exporter(Protocol):
    def export(self, metric: CallMetric) -> None: ...


class NoopExporter:
    """Default. Metrics still land in MetricsCollector; nothing external is called."""

    def export(self, metric: CallMetric) -> None:
        return


class PrometheusExporter:
    """Requires: pip install mcp-resilient[prometheus]"""

    def __init__(self) -> None:
        try:
            from prometheus_client import Counter, Histogram
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "prometheus-client not installed. Run: pip install mcp-resilient[prometheus]"
            ) from exc

        self._calls = Counter(
            "mcp_resilient_calls_total", "Total tool calls", ["tool_name", "status"]
        )
        self._latency = Histogram("mcp_resilient_latency_ms", "Tool call latency", ["tool_name"])
        self._cost = Counter("mcp_resilient_cost_usd_total", "Cumulative cost", ["tool_name"])

    def export(self, metric: CallMetric) -> None:
        self._calls.labels(tool_name=metric.tool_name, status=metric.status).inc()
        self._latency.labels(tool_name=metric.tool_name).observe(metric.latency_ms)
        self._cost.labels(tool_name=metric.tool_name).inc(metric.cost_usd)


class OpenTelemetryExporter:
    """Requires: pip install mcp-resilient[otel]"""

    def __init__(self) -> None:
        try:
            from opentelemetry import metrics as otel_metrics
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "opentelemetry not installed. Run: pip install mcp-resilient[otel]"
            ) from exc

        meter = otel_metrics.get_meter("mcp_resilient")
        self._latency_hist = meter.create_histogram("mcp_resilient.latency_ms")
        self._cost_counter = meter.create_counter("mcp_resilient.cost_usd")
        self._call_counter = meter.create_counter("mcp_resilient.calls")

    def export(self, metric: CallMetric) -> None:
        attrs = {"tool_name": metric.tool_name, "status": metric.status}
        self._call_counter.add(1, attrs)
        self._latency_hist.record(metric.latency_ms, attrs)
        self._cost_counter.add(metric.cost_usd, attrs)
