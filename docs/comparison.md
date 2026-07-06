# Landscape comparison

Checked against GitHub and PyPI (as of early 2026 — verify again before
launch, this space moves fast):

| Project | Retry+backoff | Circuit breaker | Fallback chaining | Cost tracking | Scope |
|---|---|---|---|---|---|
| **mcp-resilient** (this) | ✅ adaptive | ✅ cost-aware | ✅ | ✅ | Python, drop-in decorator |
| `mcp-circuit-breaker` | ❌ | ✅ basic | ❌ | ❌ | Python, proxy sidecar, unpublished to PyPI |
| `toolguard` | ❌ | ❌ | ❌ | ❌ | Security/prompt-injection scanning |
| `sift-gateway` | ❌ | ❌ | ❌ | ❌ | Output schema/pagination/token optimization |
| `MCPGuard` | ❌ | ❌ | ❌ | ❌ | Pre-flight CLI security scanner |
| `finemcp` | ✅ | ✅ | ✅ (load balancer) | ✅ (OTel) | **Go**, requires building server/client from scratch |

## Honest takeaways

- Nobody in the Python ecosystem combines retry + circuit breaking +
  fallback + cost tracking in one drop-in wrapper. `mcp-circuit-breaker`
  is the closest attempt but is single-feature and was never published
  to PyPI.
- `finemcp` has the most complete feature set but requires Go and a
  ground-up rebuild — it's not a wrapper for an *existing* MCP setup.
- `toolguard`, `sift-gateway`, and `MCPGuard` solve adjacent but
  different problems (security scanning, output shaping) — not reliability.
- **Cost-aware circuit breaking specifically** (tripping on cumulative $
  spend, not just failure count) does not appear in any of the above.

## Re-verify before launch

```bash
# GitHub
curl -s "https://api.github.com/search/repositories?q=mcp+circuit+breaker&sort=stars" | less

# PyPI
curl -s "https://pypi.org/pypi/<candidate-name>/json"
```

Run this again right before a public release — new entrants in this space
are likely given how fast MCP tooling is moving.
