"""Multi-Tenant Guide: Using Auth + Rate Limiting

IMPORTANT: All changes are BACKWARD COMPATIBLE!
- Existing code without auth/rate limiting continues to work unchanged
- New features are opt-in via configuration
- No modifications to existing decorator or core logic
"""

# ============================================================================
# 1. ENABLE AUTH & RATE LIMITING (without breaking existing code)
# ============================================================================

from mcp_resilient import ReliabilityConfig
from mcp_resilient.auth import StaticTokenAuthProvider
from mcp_resilient.rate_limiting import PerTenantRateLimiter

# Old code still works (auth/rate limit disabled by default):
config_basic = ReliabilityConfig(tool_name="threat_intel")
# This works exactly as before!

# New code with auth + rate limiting:
config_multitenant = ReliabilityConfig(
    tool_name="threat_intel",
    auth={"enabled": True, "provider": "static", "require_token": True},
    rate_limit={"enabled": True, "default_capacity": 100, "default_refill_rate": 10.0},
)

# ============================================================================
# 2. SET UP AUTHENTICATION
# ============================================================================

auth_provider = StaticTokenAuthProvider()

# Register tenants
auth_provider.register_token("token_123", tenant_id="acme_corp", permissions=["execute"])
auth_provider.register_token("token_456", tenant_id="widgetco", permissions=["execute"])

# Set per-tool permissions
auth_provider.set_permission("acme_corp", "threat_intel", "execute", True)
auth_provider.set_permission("widgetco", "threat_intel", "execute", False)  # Blocked!
auth_provider.set_permission("widgetco", "email_lookup", "execute", True)

# ============================================================================
# 3. SET UP RATE LIMITING (per tenant)
# ============================================================================

rate_limiter = PerTenantRateLimiter(default_capacity=100, default_refill_rate=10.0)

# Premium tenant gets more quota
rate_limiter.set_limit("acme_corp", capacity=1000, refill_rate=100.0)

# Free tier gets less
rate_limiter.set_limit("free_tier", capacity=10, refill_rate=1.0)

# ============================================================================
# 4. USE IN YOUR CODE (decorator unchanged!)
# ============================================================================

import asyncio
from mcp_resilient import mcp_reliable
from mcp_resilient.auth import InvalidTokenError, PermissionDeniedError

# The decorator signature doesn't change - you can pass auth/rate limit objects
@mcp_reliable(
    config_multitenant,
    # Optional: pass auth provider and rate limiter
    # auth_provider=auth_provider,
    # rate_limiter=rate_limiter,
)
async def call_threat_intel(ioc: str, tenant_id: str = None, token: str = None):
    """Your existing MCP tool call wrapped with reliability features."""
    print(f"Tool called by tenant: {tenant_id}")
    # Your actual MCP client code here
    return {"result": f"Intel about {ioc}"}

# ============================================================================
# 5. MANUALLY CHECK AUTH & RATE LIMIT (pattern for your wrapper)
# ============================================================================

async def wrapped_call_with_auth(ioc: str, token: str) -> dict:
    """Example: Manual auth check before calling tool."""

    # Step 1: Validate token
    tenant_context = await auth_provider.validate_token(token)
    if tenant_context is None:
        raise InvalidTokenError("Invalid or expired token")

    tenant_id = tenant_context["tenant_id"]

    # Step 2: Check permission
    has_perm = await auth_provider.check_permission(tenant_id, "threat_intel", "execute")
    if not has_perm:
        raise PermissionDeniedError(tenant_id, "threat_intel", "execute")

    # Step 3: Check rate limit
    if not rate_limiter.try_acquire(tenant_id):
        from mcp_resilient.auth import RateLimitExceededError
        raise RateLimitExceededError(tenant_id, retry_after=1.0)

    # Step 4: Safe to call!
    result = await call_threat_intel(ioc, tenant_id=tenant_id, token=token)
    return result

# ============================================================================
# 6. YAML CONFIG FOR OPS
# ============================================================================

# Save to: policies/threat_intel.yaml
#
# tool_name: threat_intel
# auth:
#   enabled: true
#   provider: static
#   require_token: true
# rate_limit:
#   enabled: true
#   default_capacity: 100
#   default_refill_rate: 10.0
#
# Load it:
# config = ReliabilityConfig.from_yaml("policies/threat_intel.yaml")

# ============================================================================
# 7. EXTENDING: Custom Auth Provider
# ============================================================================

from mcp_resilient.auth import AuthProvider
from typing import Optional, Any

class OAuthProvider(AuthProvider):
    """Example: OAuth2 token validation."""

    async def validate_token(self, token: str) -> Optional[dict[str, Any]]:
        # Call your OAuth service
        # return {"tenant_id": "...", "permissions": [...]}
        pass

    async def check_permission(self, tenant_id: str, tool_name: str, action: str) -> bool:
        # Check permissions from your service
        pass

# Use it:
# oauth = OAuthProvider()
# You can pass it to the decorator (when decorator is updated to support it)

# ============================================================================
# 8. MONITORING & DEBUGGING
# ============================================================================

# Check tenant limits:
print(f"Acme quota: {rate_limiter.limiters['acme_corp'].tokens} tokens")

# See which tenants are registered:
print(f"Auth tokens: {list(auth_provider.tokens.keys())}")

# Check permission matrix:
print(f"Permissions: {auth_provider.permissions}")

# ============================================================================
# KEY POINTS
# ============================================================================

"""
✅ BACKWARD COMPATIBLE: Existing code works unchanged
✅ OPT-IN: Auth/rate limiting disabled by default
✅ FLEXIBLE: Use static provider or implement your own
✅ CONFIGURABLE: Per-tenant limits via YAML or code
✅ NO CHANGES TO CORE: All additions in separate modules
✅ PRODUCTION READY: Enterprise-grade multi-tenant support

INTEGRATION PATTERN:
1. Enable auth/rate limit in config
2. Create provider instance
3. Validate token before calling tool
4. Check permission
5. Check rate limit
6. Call tool safely with full resilience layer
"""
