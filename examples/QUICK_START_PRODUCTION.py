"""
QUICK REFERENCE: 5-Step mcp-resilient Integration for AI Developers

Copy this checklist and follow it. That's it!
"""

# ============================================================================
# STEP 1: INSTALL
# ============================================================================
# pip install mcp-resilient

# ============================================================================
# STEP 2: CREATE CONFIG (customize for your tools)
# ============================================================================

from mcp_resilient import ReliabilityConfig, mcp_reliable
from mcp_resilient.auth import StaticTokenAuthProvider
from mcp_resilient.rate_limiting import PerTenantRateLimiter

config = ReliabilityConfig(
    tool_name="your_tool_name",
    auth={"enabled": True, "provider": "static"},
    rate_limit={"enabled": True, "default_capacity": 100}
)

# ============================================================================
# STEP 3: SETUP AUTH & RATE LIMIT
# ============================================================================

auth = StaticTokenAuthProvider()
auth.register_token("token_123", tenant_id="your_tenant", permissions=["execute"])
auth.set_permission("your_tenant", "your_tool_name", "execute", True)

limiter = PerTenantRateLimiter(default_capacity=100, default_refill_rate=10.0)

# ============================================================================
# STEP 4: DECORATE YOUR TOOL
# ============================================================================

@mcp_reliable(config)
async def call_your_tool(param1: str, tool_name: str = "your_tool_name"):
    """Wrapped tool call - gets retry/circuit-break/fallback automatically."""
    # Your MCP client call here
    return {"result": f"Processed {param1}"}

# ============================================================================
# STEP 5: CREATE SAFE WRAPPER (THE IMPORTANT PART!)
# ============================================================================

from mcp_resilient.auth import InvalidTokenError, PermissionDeniedError, RateLimitExceededError

async def safe_call(param1: str, token: str) -> dict:
    """
    THIS is what your LLM framework calls!
    
    All security checks here:
    ✓ Validate token
    ✓ Check permission
    ✓ Check rate limit
    ✓ Call tool safely
    """
    
    # 1. Validate token
    tenant_context = await auth.validate_token(token)
    if tenant_context is None:
        raise InvalidTokenError("Invalid token")
    
    tenant_id = tenant_context["tenant_id"]
    
    # 2. Check permission
    has_perm = await auth.check_permission(tenant_id, "your_tool_name", "execute")
    if not has_perm:
        raise PermissionDeniedError(tenant_id, "your_tool_name", "execute")
    
    # 3. Check rate limit
    if not limiter.try_acquire(tenant_id):
        raise RateLimitExceededError(tenant_id, retry_after=5.0)
    
    # 4. Safe to call!
    return await call_your_tool(param1)

# ============================================================================
# USAGE IN YOUR LLM HANDLER
# ============================================================================

# In your Claude/GPT integration:
async def handle_tool_call(tool_name, params, user_token):
    """LLM calls this when it wants to use a tool."""
    
    if tool_name == "your_tool_name":
        try:
            result = await safe_call(params["param1"], user_token)
            return result
        except InvalidTokenError:
            return "Error: Invalid authentication"
        except PermissionDeniedError:
            return "Error: You don't have access to this tool"
        except RateLimitExceededError as e:
            return f"Error: Rate limit exceeded. Retry after {e.retry_after}s"

# ============================================================================
# PRODUCTION CHECKLIST
# ============================================================================

"""
✅ BEFORE DEPLOY:
   [ ] Use real auth service (not StaticTokenAuthProvider)
   [ ] Load secrets from env/vault (not hardcoded)
   [ ] Set up Prometheus monitoring
   [ ] Configure rate limits per tenant type
   [ ] Test error scenarios
   [ ] Load test with expected traffic
   [ ] Set up alerts for circuit breaks

✅ MONITORING:
   [ ] Watch response latency
   [ ] Monitor success rate (should be 99%+)
   [ ] Track retry count
   [ ] Alert on circuit opens
   [ ] Monitor cost per tenant
   [ ] Track auth failures

✅ THAT'S IT! You're production-ready!
"""

# ============================================================================
# COMMON ISSUES & FIXES
# ============================================================================

"""
ISSUE: "Circuit breaker keeps opening"
FIX: Check upstream service health, increase cooldown time

ISSUE: "High latency from retries"
FIX: Reduce max_attempts, increase base_delay

ISSUE: "Token validation failing"
FIX: Ensure token is valid, check expiry time

ISSUE: "Permission denied for good users"
FIX: Check auth.set_permission() configuration

ISSUE: "Rate limit exhausted too quickly"
FIX: Increase capacity or refill_rate for that tenant
"""

# ============================================================================
# FILE TO CUSTOMIZE
# ============================================================================

"""
👉 Copy this to your project:
   examples/production_ai_agent_setup.py
   
Then customize:
   1. Replace "threat_intel" with your tool name
   2. Replace mock API call with real MCP client
   3. Load secrets from env/vault
   4. Connect to real auth service
   5. Export metrics to Prometheus
"""

print("✅ You're ready to deploy mcp-resilient in production!")
