# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/), versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Roadmap

- Per-fallback-hop circuit breaking (currently primary-tool-only, see `docs/architecture.md`).
- MLflow exporter.
- DynamoDB `StateStore` implementation.

## [0.1.0] - 2026-07-06

### Added

- Refactored `@mcp_reliable` decorator to support direct keyword arguments (e.g., `@mcp_reliable(retry=...)`) and parameter-less usage (e.g., `@mcp_reliable`).
- Custom `TypeError` validation inside `@mcp_reliable` to provide clear guidance on invalid settings or types.
- Created `tests/test_docs_examples.py` for CI-checked doc-sync, running README/Quickstart examples.
- Documented `AuthConfig` details and explicit compliance warnings (resilience layer != encryption/cryptographic compliance layer).
- Added badges (CI, Coverage, PyPI) to README.

## [0.1.1] - 2026-07-06

### Fixed

- Replaced relative documentation and license links in README with absolute URLs to resolve 404 errors on PyPI.

## [0.1.0] - 2026-07-03

### Added

- `@mcp_reliable` decorator: retry, circuit breaking, fallback, observability.
- Adaptive backoff: fixed / exponential / decorrelated jitter.
- Cost-aware circuit breaker (trips on failure count OR cumulative $ spend).
- Ordered fallback chain routing.
- `InMemoryStateStore` (default) and `RedisStateStore` (optional, distributed).
- `PrometheusExporter` and `OpenTelemetryExporter` (both optional).
- `mcp-resilient simulate` CLI — dry-run a policy against synthetic failures.
- LangChain/LangGraph tool adapter (`integrations/langchain_adapter.py`).
- YAML policy loading via `ReliabilityConfig.from_yaml()`.
