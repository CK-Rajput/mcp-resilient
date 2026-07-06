"""
PRODUCTION-GRADE AI AGENT SETUP: mcp-resilient Integration Guide

For AI developers deploying Claude, GPT, or other LLMs with MCP tools.
Real-world patterns, security best practices, and error handling.
"""

import asyncio
import os
from typing import Optional, Any
from datetime import datetime

from mcp_resilient import (
    ReliabilityConfig,
    mcp_reliable,
    CircuitOpenError,
    RetryExhaustedError,
    FallbackExhaustedError,
)
from mcp_resilient.auth import StaticTokenAuthProvider, InvalidTokenError, PermissionDeniedError
from mcp_resilient.rate_limiting import PerTenantRateLimiter
from mcp_resilient.auth import RateLimitExceededError


# ============================================================================
# PART 1: ENVIRONMENT & SECRETS SETUP
# ============================================================================

class ProductionSecrets:
    """Load secrets from environment (use .env or secret manager in production)."""

    @staticmethod
    def get_api_token() -> str:
        """Get API token from environment."""
        token = os.getenv("LLM_API_KEY")
        if not token:
            raise ValueError("LLM_API_KEY not set in environment")
        return token

    @staticmethod
    def get_tenant_id() -> str:
        """Get tenant ID from environment or request context."""
        tenant = os.getenv("TENANT_ID", "default_tenant")
        return tenant

    @staticmethod
    def get_log_level() -> str:
        """Get log level for production."""
        return os.getenv("LOG_LEVEL", "INFO")


# ============================================================================
# PART 2: SETUP AUTH PROVIDER (Enterprise Pattern)
# ============================================================================

def setup_auth_provider() -> StaticTokenAuthProvider:
    """
    Initialize authentication provider for production.
    
    In real deployment:
    - Connect to OAuth2 service
    - Use Redis for token caching
    - Implement token refresh
    - Add audit logging
    """
    auth = StaticTokenAuthProvider()

    # Example: Register your production tenants
    # In real setup: Load from database or service
    auth.register_token(
        "sk-prod-acme-12345",
        tenant_id="acme_corp",
        permissions=["execute", "read_results"]
    )
    auth.register_token(
        "sk-prod-widgetco-67890",
        tenant_id="widget_co",
        permissions=["execute"]
    )

    # Set tool permissions per tenant
    auth.set_permission("acme_corp", "threat_intel", "execute", True)
    auth.set_permission("acme_corp", "email_verify", "execute", True)
    auth.set_permission("widget_co", "email_verify", "execute", True)
    auth.set_permission("widget_co", "threat_intel", "execute", False)  # Blocked!

    return auth


# ============================================================================
# PART 3: SETUP RATE LIMITING (Cost Control)
# ============================================================================

def setup_rate_limiter() -> PerTenantRateLimiter:
    """
    Initialize rate limiter for cost control.
    
    Prevents runaway API calls during LLM loops.
    """
    limiter = PerTenantRateLimiter(
        default_capacity=50,         # 50 calls/bucket
        default_refill_rate=5.0      # 5 calls/sec refill
    )

    # Premium tenant: 1000 calls/bucket, 100/sec refill
    limiter.set_limit("acme_corp", capacity=1000, refill_rate=100.0)

    # Free tier: 10 calls/bucket, 1/sec refill
    limiter.set_limit("widget_co", capacity=10, refill_rate=1.0)

    return limiter


# ============================================================================
# PART 4: RELIABILITY CONFIG (Production Settings)
# ============================================================================

def create_reliability_config(tool_name: str) -> ReliabilityConfig:
    """
    Create production-grade reliability config.
    
    Conservative defaults that work for AI agents:
    - 3 retries (don't overwhelm LLM)
    - Exponential backoff (smooth recovery)
    - Cost-aware circuit breaker ($10/hour limit)
    """
    return ReliabilityConfig(
        tool_name=tool_name,
        
        # Retry: Aggressive enough to handle transient failures
        retry={
            "enabled": True,
            "max_attempts": 3,
            "timeout_seconds": 30.0,  # Long timeout for AI agent context
            "backoff": {
                "strategy": "exponential",
                "base_delay": 1.0,
                "max_delay": 60.0,
                "multiplier": 2.0,
            }
        },
        
        # Circuit breaker: Prevents cascading failures
        circuit_breaker={
            "enabled": True,
            "failure_threshold": 5,      # 5 consecutive failures
            "window_seconds": 300.0,     # 5 minute window
            "cooldown_seconds": 60.0,    # Wait 1 min before retry
            "cost_budget": 10.0,         # $10 per window
        },
        
        # Fallback: Try backup tools if primary fails
        fallback={
            "enabled": True,
            "tool_chain": [f"{tool_name}_backup", f"{tool_name}_cached"]
        },
        
        # Auth & Rate limiting: Multi-tenant support
        auth={
            "enabled": True,
            "provider": "static",
            "require_token": True,
        },
        
        rate_limit={
            "enabled": True,
            "default_capacity": 50,
            "default_refill_rate": 5.0,
        },
        
        # Observability: Track everything
        observability={
            "enabled": True,
            "exporter": "prometheus",  # Or 'otel' for distributed tracing
            "log_level": ProductionSecrets.get_log_level(),
        }
    )


# ============================================================================
# PART 5: DECORATED TOOL WRAPPER (The AI Agent Calls This)
# ============================================================================

config = create_reliability_config("threat_intel")
auth_provider = setup_auth_provider()
rate_limiter = setup_rate_limiter()


@mcp_reliable(config)
async def call_threat_intel(
    ioc: str,
    tenant_id: str = "default_tenant",
    tool_name: str = "threat_intel"
) -> dict:
    """
    Wrapped threat intelligence lookup tool.
    
    The LLM agent calls this, all resilience features are automatic:
    - Retries on transient failures
    - Circuit breaks on persistent failures
    - Falls back to backup tools
    - Tracks cost
    - Logs everything
    
    Args:
        ioc: Indicator of compromise (domain, IP, hash)
        tenant_id: Which tenant is calling
        tool_name: Which tool to use (for fallback routing)
    
    Returns:
        Threat intelligence result dict
        
    Raises:
        CircuitOpenError: Tool is too broken, skip it
        RateLimitExceededError: Too many calls, wait
        PermissionDeniedError: Tenant not allowed
    """
    # This is where your actual MCP client call would go
    # Example: await mcp_client.call_tool(tool_name, {"ioc": ioc})
    
    print(f"✓ Tool '{tool_name}' called by {tenant_id} for IOC: {ioc}")
    
    # Simulate API call
    await asyncio.sleep(0.1)
    
    return {
        "ioc": ioc,
        "is_malicious": False,
        "confidence": 0.95,
        "last_seen": datetime.now().isoformat(),
        "sources": ["abuse.ch", "urlhaus", "phishtank"],
    }


# ============================================================================
# PART 6: PRODUCTION WRAPPER (Handles Auth + Rate Limiting)
# ============================================================================

async def safe_tool_call(
    ioc: str,
    token: str,
    tool_name: str = "threat_intel"
) -> dict:
    """
    Production-grade tool call with full safety checks.
    
    This is what your AI agent framework calls.
    ALL security checks happen here.
    
    Flow:
    1. Validate token
    2. Check permission
    3. Check rate limit
    4. Call tool with retry/circuit break/fallback
    5. Return result or raise safe error
    """

    # Step 1: VALIDATE TOKEN
    print(f"\n🔐 Step 1: Validating token...")
    tenant_context = await auth_provider.validate_token(token)
    if tenant_context is None:
        raise InvalidTokenError("Invalid or expired token")

    tenant_id = tenant_context["tenant_id"]
    print(f"  ✓ Token valid for tenant: {tenant_id}")

    # Step 2: CHECK PERMISSION
    print(f"📋 Step 2: Checking permissions...")
    has_perm = await auth_provider.check_permission(tenant_id, tool_name, "execute")
    if not has_perm:
        raise PermissionDeniedError(tenant_id, tool_name, "execute")
    print(f"  ✓ Permission granted for {tool_name}")

    # Step 3: CHECK RATE LIMIT
    print(f"⏱️  Step 3: Checking rate limit...")
    if not rate_limiter.try_acquire(tenant_id):
        raise RateLimitExceededError(tenant_id, retry_after=5.0)
    print(f"  ✓ Rate limit OK (tokens available)")

    # Step 4: CALL TOOL WITH FULL RESILIENCE
    print(f"🔄 Step 4: Calling tool with resilience layer...")
    try:
        result = await call_threat_intel(
            ioc=ioc,
            tenant_id=tenant_id,
            tool_name=tool_name
        )
        print(f"  ✓ Call succeeded: {result}")
        return result

    except CircuitOpenError as e:
        print(f"  ⚠️  Circuit open: {e}")
        # AI agent should handle gracefully - maybe use fallback or cache
        raise

    except RetryExhaustedError as e:
        print(f"  ❌ All retries exhausted: {e}")
        raise

    except FallbackExhaustedError as e:
        print(f"  ❌ Fallback chain exhausted: {e}")
        raise


# ============================================================================
# PART 7: AI AGENT INTEGRATION EXAMPLE
# ============================================================================

class AIAgentToolExecutor:
    """
    Pattern for integrating with Claude/GPT/Other LLMs.
    
    The LLM receives tools via MCP, calls them through your framework,
    this executor handles auth + resilience.
    """

    def __init__(self, tenant_id: str, api_token: str):
        self.tenant_id = tenant_id
        self.api_token = api_token

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool call from LLM with safety.
        
        LLM sends: {"name": "threat_intel", "arguments": {"ioc": "example.com"}}
        
        This method:
        1. Routes to correct tool
        2. Applies auth checks
        3. Applies rate limiting
        4. Retries on failure
        5. Returns safe result
        """

        if tool_name == "threat_intel":
            ioc = kwargs.get("ioc")
            if not ioc:
                raise ValueError("ioc parameter required")

            return await safe_tool_call(
                ioc=ioc,
                token=self.api_token,
                tool_name=tool_name
            )

        elif tool_name == "email_verify":
            email = kwargs.get("email")
            if not email:
                raise ValueError("email parameter required")

            # Similar pattern for other tools
            return await safe_tool_call(
                ioc=email,
                token=self.api_token,
                tool_name=tool_name
            )

        else:
            raise ValueError(f"Unknown tool: {tool_name}")


# ============================================================================
# PART 8: ERROR HANDLING FOR AI AGENTS
# ============================================================================

async def run_ai_agent_safely(agent_query: str, tenant_id: str, api_token: str) -> str:
    """
    Example: Run LLM agent query with safe error handling.
    
    Pattern to follow in your actual LLM framework:
    """

    executor = AIAgentToolExecutor(tenant_id, api_token)

    try:
        # Step 1: LLM gets tools via MCP
        print(f"\n🤖 Starting AI agent for query: {agent_query}")
        print(f"   Tenant: {tenant_id}")

        # Step 2: LLM decides to call a tool
        tool_name = "threat_intel"
        kwargs = {"ioc": "example.com"}

        print(f"\n📞 LLM calling tool: {tool_name}({kwargs})")

        # Step 3: Safe execution
        result = await executor.execute_tool(tool_name, **kwargs)

        print(f"\n✅ Result: {result}")
        return f"Agent completed. Result: {result}"

    except InvalidTokenError as e:
        print(f"\n🚫 Auth Error: {e}")
        return "Error: Invalid authentication token. Please check credentials."

    except PermissionDeniedError as e:
        print(f"\n🚫 Permission Error: {e}")
        return "Error: Your tenant is not authorized for this tool."

    except RateLimitExceededError as e:
        print(f"\n⏳ Rate Limit Error: {e}")
        return f"Error: Rate limit exceeded. Retry after {e.retry_after}s"

    except CircuitOpenError as e:
        print(f"\n⛔ Circuit Open: {e}")
        return "Error: Tool temporarily unavailable. Retrying in 30s..."

    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        # IMPORTANT: Log to your monitoring system
        return f"Error: {str(e)}"


# ============================================================================
# PART 9: MONITORING & OBSERVABILITY
# ============================================================================

class ProductionMonitoring:
    """Emit metrics to your monitoring system."""

    @staticmethod
    def log_tool_call(tool_name: str, tenant_id: str, status: str, duration_ms: float):
        """Log to CloudWatch, Datadog, etc."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "tenant": tenant_id,
            "status": status,
            "duration_ms": duration_ms,
        }
        print(f"📊 METRIC: {log_entry}")
        # In production: await cloudwatch.put_metric_data(...)

    @staticmethod
    def alert_circuit_open(tool_name: str):
        """Send alert when circuit opens."""
        print(f"🚨 ALERT: Circuit opened for tool '{tool_name}'")
        # In production: await slack.send_message(f"Circuit open: {tool_name}")


# ============================================================================
# MAIN: RUN PRODUCTION DEMO
# ============================================================================

async def main():
    """Production-ready demo with multiple scenarios."""

    print("=" * 80)
    print("PRODUCTION AI AGENT SETUP: mcp-resilient")
    print("=" * 80)

    # Scenario 1: Valid tenant, valid token, good call
    print("\n" + "=" * 80)
    print("SCENARIO 1: Valid tenant with valid call")
    print("=" * 80)
    try:
        result = await run_ai_agent_safely(
            agent_query="Is example.com malicious?",
            tenant_id="acme_corp",
            api_token="sk-prod-acme-12345"
        )
        print(f"Final result: {result}")
    except Exception as e:
        print(f"Error: {e}")

    # Scenario 2: Permission denied
    print("\n" + "=" * 80)
    print("SCENARIO 2: Tenant without permission (widget_co tries threat_intel)")
    print("=" * 80)
    try:
        result = await run_ai_agent_safely(
            agent_query="Is example.com malicious?",
            tenant_id="widget_co",
            api_token="sk-prod-widgetco-67890"
        )
        print(f"Final result: {result}")
    except Exception as e:
        print(f"Error: {e}")

    # Scenario 3: Invalid token
    print("\n" + "=" * 80)
    print("SCENARIO 3: Invalid token")
    print("=" * 80)
    try:
        result = await run_ai_agent_safely(
            agent_query="Is example.com malicious?",
            tenant_id="unknown",
            api_token="invalid-token-xyz"
        )
        print(f"Final result: {result}")
    except Exception as e:
        print(f"Error: {e}")

    # Scenario 4: Rate limit test
    print("\n" + "=" * 80)
    print("SCENARIO 4: Rate limit (widget_co has very low limit)")
    print("=" * 80)
    for i in range(3):
        try:
            print(f"\nAttempt {i + 1}:")
            result = await run_ai_agent_safely(
                agent_query=f"Check query {i}",
                tenant_id="widget_co",
                api_token="sk-prod-widgetco-67890"
            )
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")

    print("\n" + "=" * 80)
    print("✅ PRODUCTION DEMO COMPLETE")
    print("=" * 80)
    print("\nNEXT STEPS:")
    print("1. Replace mock API calls with real MCP client")
    print("2. Load secrets from env/vault, not hardcoded")
    print("3. Connect auth provider to your auth service (OAuth, SAML, etc)")
    print("4. Export metrics to Prometheus/Datadog/CloudWatch")
    print("5. Set up alerting for circuit breaker trips")
    print("6. Load rate limits from database per tenant")
    print("7. Add request tracing (OpenTelemetry)")
    print("8. Monitor LLM token usage in combination with tool calls")


if __name__ == "__main__":
    asyncio.run(main())
