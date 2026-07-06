from __future__ import annotations

import pytest

from mcp_resilient.observability.metrics import CallMetric, MetricsCollector


def test_metrics_summary_computes_aggregates():
    collector = MetricsCollector()
    collector.record(CallMetric("t", 0.0, 100.0, "success", cost_usd=0.01, retry_count=0))
    collector.record(CallMetric("t", 0.0, 300.0, "failure", cost_usd=0.02, retry_count=2))

    summary = collector.summary("t")

    assert summary["count"] == 2
    assert summary["success_rate"] == 0.5
    assert summary["avg_latency_ms"] == 200.0
    assert summary["total_cost_usd"] == pytest.approx(0.03)
    assert summary["total_retries"] == 2


def test_metrics_summary_empty_when_no_records():
    collector = MetricsCollector()
    assert collector.summary("nonexistent") == {"count": 0}


def test_metrics_summary_filters_by_tool_name():
    collector = MetricsCollector()
    collector.record(CallMetric("a", 0.0, 50.0, "success"))
    collector.record(CallMetric("b", 0.0, 999.0, "success"))

    summary = collector.summary("a")
    assert summary["count"] == 1
    assert summary["avg_latency_ms"] == 50.0
