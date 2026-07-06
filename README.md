# mcp-resilient

[![CI Status](https://github.com/ck-rajput/mcp-resilient/actions/workflows/ci.yml/badge.svg)](https://github.com/ck-rajput/mcp-resilient/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/badge/pypi-v0.0.1-blue.svg)](https://pypi.org/project/mcp-resilient/)
[![License](https://img.shields.io/pypi/l/mcp-resilient.svg)](https://github.com/ck-rajput/mcp-resilient/blob/main/LICENSE)

**Drop-in reliability layer for MCP tool calls.** Adaptive retry, cost-aware circuit
breaking, ordered fallback chains, and pluggable observability - as a decorator
around any existing MCP client. No protocol changes, no rebuild.

```python
from mcp_resilient import ReliabilityConfig, mcp_reliable

config = ReliabilityConfig(tool_name="threat_intel_lookup")

@mcp_reliable(config)
async def call_threat_intel(ioc: str):
    return await mcp_client.call_tool("threat_intel_lookup", {"ioc": ioc})
```

## Why this exists

How agents _discover and call_ tools is defined by MCP. Does not indicate what
Occurs when a tool is slow or flaky or rate-limited that's left to each.
developer to reinvent. A number of projects interface abutting troubles security
None of them provide retry+circuit breaking+output-size reduction + fallback

- cost tracking in a Python native drop in wrapper.

See [`docs/comparison.md`](https://github.com/ck-rajput/mcp-resilient/blob/main/docs/comparison.md) for the full landscape check.

## Install

```bash
pip install mcp-resilient            # core
pip install mcp-resilient[redis]     # + distributed state for multi-instance agents
pip install mcp-resilient[otel]      # + OpenTelemetry metrics export
pip install mcp-resilient[prometheus] # + Prometheus metrics export
pip install mcp-resilient[cli]       # + `mcp-resilient simulate` command
```

## Features

- **Adaptive retry:** fixed, exponential, or decorrelated-jitter backoff (AWS-style, avoids thundering herd on shared upstreams).
- **Cost-aware circuit breaker:** trips on failure count or cumulative $ spend in a window, whichever fires first.
- **Fallback chains:** ordered list of fallback tools, tried in sequence.
- **Observability:** Prometheus / OpenTelemetry exporters.
- **Pluggable state:** in-memory by default, Redis for multi-instance agents.
- **`mcp-resilient simulate`:** dry-run a policy against synthetic failures before it ever touches production.

## Real-world Example (SecOps/SIEM)

For a practical example, see [examples/siem_threat_intel_example.py](https://github.com/ck-rajput/mcp-resilient/blob/main/examples/siem_threat_intel_example.py). It demonstrates a real SecOps pattern:

- A primary threat intelligence enrichment API call (which might be flaky or rate-limited).
- A free backup API fallback.
- A cost-aware circuit breaker to prevent retries from exceeding your primary API budget.

## Quickstart

See [`docs/quickstart.md`](https://github.com/ck-rajput/mcp-resilient/blob/main/docs/quickstart.md) and the runnable scripts in [`examples/`](https://github.com/ck-rajput/mcp-resilient/tree/main/examples).

## Architecture

See [`docs/architecture.md`](https://github.com/ck-rajput/mcp-resilient/blob/main/docs/architecture.md) for the HLD/LLD.

## Development

```bash
git clone https://github.com/ck-rajput/mcp-resilient
cd mcp-resilient
pip install -e ".[dev,cli]"
pytest -q
```

## Scope & Compliance Warning

> [!WARNING]
> `mcp-resilient` is a **resilience and access-control routing layer**, NOT a data encryption or cryptographic compliance vault. For highly regulated environments (like finance PCI-DSS, SOC2 or healthcare), data encryption (at rest and in transit), credential storage security, and compliance auditing need to be performed in your main hosting infrastructure.

## License

MIT - see [LICENSE](https://github.com/ck-rajput/mcp-resilient/blob/main/LICENSE).
