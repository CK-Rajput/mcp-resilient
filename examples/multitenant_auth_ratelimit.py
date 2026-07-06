"""Multi-tenant example: using auth + rate limiting with mcp-resilient.

Demonstrates:
  1. Per-tenant authentication via tokens
  2. Per-tenant rate limiting (token bucket)
  3. Permission checking
  4. All integrated with the existing retry/circuit-breaker layer
"""

import asyncio

from mcp_resilient import ReliabilityConfig
from mcp_resilient.auth import InvalidTokenError, PermissionDeniedError, StaticTokenAuthProvider
from mcp_resilient.rate_limiting import PerTenantRateLimiter


async def simulate_mcp_call(tool_name: str, ioc: str) -> dict:
    """Simulate an MCP tool call."""
    print(f"✓ Tool '{tool_name}' called with IOC: {ioc}")
    await asyncio.sleep(0.1)
    return {"result": f"info about {ioc}"}


async def main():
    print("=" * 70)
    print("Multi-Tenant Example: Auth + Rate Limiting")
    print("=" * 70)

    # 1. Set up authentication
    print("\n📋 Setting up Authentication...")
    auth_provider = StaticTokenAuthProvider()

    # Register two tenants
    auth_provider.register_token("token_acme", "acme_corp", ["execute"])
    auth_provider.register_token("token_widgetco", "widget_co", ["execute"])

    # Set permissions: acme_corp can use threat_intel, widget_co cannot
    auth_provider.set_permission("acme_corp", "threat_intel", "execute", True)
    auth_provider.set_permission("widget_co", "threat_intel", "execute", False)
    auth_provider.set_permission("widget_co", "email_lookup", "execute", True)

    print("  ✓ Registered tenant: acme_corp (token: token_acme)")
    print("  ✓ Registered tenant: widget_co (token: token_widgetco)")

    # 2. Set up rate limiting
    print("\n⏱️  Setting up Rate Limiting...")
    rate_limiter = PerTenantRateLimiter(default_capacity=5, default_refill_rate=1.0)

    # acme_corp gets 10 calls/sec, widget_co gets 2 calls/sec
    rate_limiter.set_limit("acme_corp", capacity=10, refill_rate=2.0)
    rate_limiter.set_limit("widget_co", capacity=2, refill_rate=0.5)

    print("  ✓ acme_corp: 10 calls/bucket, 2 calls/sec")
    print("  ✓ widget_co: 2 calls/bucket, 0.5 calls/sec")

    # 3. Create reliability config (unchanged)
    print("\n⚙️  Creating Reliability Config...")
    config = ReliabilityConfig(
        tool_name="threat_intel",
        auth={"enabled": True, "provider": "static"},
        rate_limit={"enabled": True, "default_capacity": 5, "default_refill_rate": 1.0},
    )
    print(f"  ✓ Config: {config.tool_name}")
    print(f"    - Auth enabled: {config.auth.enabled}")
    print(f"    - Rate limit enabled: {config.rate_limit.enabled}")

    # 4. Demonstrate scenarios
    print("\n" + "=" * 70)
    print("SCENARIO 1: Valid token + valid permission + rate limit OK")
    print("=" * 70)

    token = "token_acme"
    tenant_context = await auth_provider.validate_token(token)

    if tenant_context is None:
        print("  ❌ Invalid token!")
    else:
        tenant_id = tenant_context["tenant_id"]
        print(f"  ✓ Token valid for tenant: {tenant_id}")

        # Check permission
        has_perm = await auth_provider.check_permission(tenant_id, "threat_intel", "execute")
        if not has_perm:
            raise PermissionDeniedError(tenant_id, "threat_intel", "execute")
        print(f"  ✓ Permission granted: {tenant_id} can execute threat_intel")

        # Check rate limit
        if rate_limiter.try_acquire(tenant_id):
            result = await simulate_mcp_call("threat_intel", "example.com")
            print(f"  ✓ Rate limit OK, call succeeded: {result}")
        else:
            raise Exception(f"Rate limit exceeded for {tenant_id}")

    # 5. Demonstrate permission denial
    print("\n" + "=" * 70)
    print("SCENARIO 2: Valid token but NO permission (widget_co)")
    print("=" * 70)

    token = "token_widgetco"
    tenant_context = await auth_provider.validate_token(token)

    if tenant_context is None:
        print("  ❌ Invalid token!")
    else:
        tenant_id = tenant_context["tenant_id"]
        print(f"  ✓ Token valid for tenant: {tenant_id}")

        # Check permission
        has_perm = await auth_provider.check_permission(tenant_id, "threat_intel", "execute")
        if not has_perm:
            print(f"  ❌ Permission DENIED: {tenant_id} cannot execute threat_intel")
        else:
            print(f"  ✓ Permission granted, call succeeded")

    # 6. Demonstrate rate limiting (different tenant)
    print("\n" + "=" * 70)
    print("SCENARIO 3: Rate limit check (widget_co, 2 calls/bucket)")
    print("=" * 70)

    tenant_id = "widget_co"
    tool_name = "email_lookup"

    print(f"  Attempting 3 rapid calls for {tenant_id}...")
    for i in range(3):
        if rate_limiter.try_acquire(tenant_id):
            result = await simulate_mcp_call(tool_name, f"test{i}@example.com")
            print(f"    Call {i + 1}: ✓ OK (rate limit has tokens)")
        else:
            print(f"    Call {i + 1}: ❌ BLOCKED (rate limit exhausted)")

    # 7. Show config export
    print("\n" + "=" * 70)
    print("CONFIG STRUCTURE (for YAML export)")
    print("=" * 70)
    print(f"\ntool_name: {config.tool_name}")
    print(f"auth:")
    print(f"  enabled: {config.auth.enabled}")
    print(f"  provider: {config.auth.provider}")
    print(f"  require_token: {config.auth.require_token}")
    print(f"rate_limit:")
    print(f"  enabled: {config.rate_limit.enabled}")
    print(f"  default_capacity: {config.rate_limit.default_capacity}")
    print(f"  default_refill_rate: {config.rate_limit.default_refill_rate}")

    print("\n✅ Multi-tenant example complete!")


if __name__ == "__main__":
    asyncio.run(main())
