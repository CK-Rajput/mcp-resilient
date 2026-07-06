from __future__ import annotations

import asyncio
import random

try:
    import typer
except ImportError as exc:  # pragma: no cover
    raise ImportError("typer not installed. Run: pip install mcp-resilient[cli]") from exc

from mcp_resilient.circuit_breaker.breaker import CircuitBreaker
from mcp_resilient.circuit_breaker.state_store import BreakerStateStore
from mcp_resilient.core.config import ReliabilityConfig
from mcp_resilient.storage.memory_store import InMemoryStateStore

app = typer.Typer(help="mcp-resilient: reliability layer for MCP tool calls.")


@app.callback()
def _main() -> None:
    """mcp-resilient — reliability layer for MCP tool calls.

    An explicit callback here keeps subcommand style (`mcp-resilient simulate ...`)
    stable even with a single command today, so it doesn't shift once more
    commands (e.g. `validate`, `benchmark`) are added.
    """


@app.command()
def simulate(
    config_path: str = typer.Argument(..., help="Path to a YAML ReliabilityConfig."),
    failure_rate: float = typer.Option(0.3, help="Simulated failure probability per call."),
    calls: int = typer.Option(50, help="Number of simulated calls."),
    cost_per_call: float = typer.Option(0.01, help="Simulated $ cost per failed call."),
) -> None:
    """Dry-run a reliability policy against a synthetic failure pattern —
    see how many calls get blocked and how much cost is saved BEFORE
    wiring the policy into a real agent. No existing tool in this space
    offers a pre-deploy simulator for reliability config specifically.
    """

    async def _run() -> None:
        config = ReliabilityConfig.from_yaml(config_path)
        store = InMemoryStateStore()
        breaker = CircuitBreaker(config.tool_name, config.circuit_breaker, BreakerStateStore(store))

        blocked_calls = 0
        failed_calls = 0
        wasted_cost = 0.0

        for _ in range(calls):
            try:
                await breaker.before_call()
            except Exception:
                blocked_calls += 1
                continue

            if random.random() < failure_rate:
                failed_calls += 1
                wasted_cost += cost_per_call
                await breaker.record_failure(cost=cost_per_call)
            else:
                await breaker.record_success()

        typer.echo(f"Tool: {config.tool_name}")
        typer.echo(f"Simulated {calls} calls at {failure_rate:.0%} failure rate")
        typer.echo(f"Failed calls: {failed_calls}")
        typer.echo(f"Blocked by open circuit (saved from hitting upstream): {blocked_calls}")
        typer.echo(f"Cost spent on failures: ${wasted_cost:.4f}")
        if config.circuit_breaker.cost_budget:
            typer.echo(f"Cost budget configured: ${config.circuit_breaker.cost_budget:.4f}")

    asyncio.run(_run())


if __name__ == "__main__":
    app()
