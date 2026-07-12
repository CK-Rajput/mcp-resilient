# mcp-resilient — Project Document

## Problem Statement
MCP (Model Context Protocol) tool calls in production AI agents lack a standardized resilience layer. When tools are slow, rate-limited, or flaky, each developer hand-rolls retry logic, circuit breakers, and fallbacks — wasting effort and introducing inconsistent failure behavior across agent systems.

## Problem Goal
Provide a **drop-in Python decorator** that wraps any MCP `call_tool` invocation with production-grade reliability: adaptive retry, cost-aware circuit breaking, ordered fallback chains, and pluggable observability — without modifying the underlying MCP protocol or client.

## Approach
Wrap existing MCP client calls with a composable decorator (`@mcp_reliable`) backed by:
- **Retry engine** — fixed, exponential, or decorrelated-jitter (AWS-style) backoff
- **Circuit breaker** — trips on failure count *or* cumulative cost budget exceeded
- **Fallback chain** — ordered list of backup tools tried in sequence on exhaustion
- **Observability** — Prometheus / OpenTelemetry exporters; in-memory or Redis state

## Algorithm / Model
1. Call primary tool → on failure, apply backoff strategy and retry up to `max_attempts`
2. If retries exhausted → check circuit state; if OPEN, skip to fallback immediately
3. Evaluate cost window: if `$spend ≥ budget`, trip circuit regardless of failure count
4. Iterate fallback list in order; return first success or raise `FallbackExhaustedError`
5. Emit span/metric on every attempt outcome

## My Responsibilities (as AI/ML Engineer)
- Design `ReliabilityConfig` schema (Pydantic v2) covering all policy knobs
- Implement and unit-test retry, circuit-breaker, fallback, rate-limiting, and deduplication modules
- Write integration tests, add edge-case fixtures, maintain ≥ 90% coverage
- Refactor module boundaries, enforce type safety (`mypy`), and lint (`ruff`)
- Author quickstart, API reference, architecture, and comparison docs
- Publish to PyPI with semantic versioning and a GitHub Actions CI pipeline

## Expected Output
A pip-installable package (`mcp-resilient`) that reduces tool-call failure rate in production agents by ≥ 80% with zero protocol changes.

## Obtained Output
`v0.1.0` published on PyPI. Core decorator functional with retry, circuit-breaker, and fallback. Observability exporters (Prometheus/OTel) and Redis state backend available as extras. CLI `mcp-resilient simulate` ships with `[cli]` extra.

## Conclusion
`mcp-resilient` fills a critical gap in the MCP ecosystem by centralizing resilience concerns into a single, testable, configurable decorator — enabling reliable production AI agents without per-project boilerplate.

---

## STAR Format

| | |
|---|---|
| **Situation** | Production AI agents using MCP tools experienced cascading failures during rate-limit spikes and transient upstream errors, with no shared resilience standard across projects. |
| **Task** | Build and publish a Python library that provides retry, circuit-breaking, fallback, and observability as a zero-friction decorator around any MCP client call. |
| **Action** | Designed a Pydantic-based config schema; implemented pluggable retry strategies (jitter backoff), cost-aware circuit breaker, ordered fallback chains, Prometheus/OTel exporters, and Redis-backed distributed state; wrote tests and docs; set up CI/CD and PyPI release pipeline. |
| **Result** | Delivered `mcp-resilient v0.1.0` — installable in one line, reducing agent tool-call failure rates by targeting ≥ 80% improvement, with a `simulate` CLI for policy dry-runs before production deployment. |
