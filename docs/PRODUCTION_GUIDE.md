# 🚀 PRODUCTION GUIDE: mcp-resilient for AI Developers

## Quick Summary (Hinglish)

Agar tum **Claude, GPT, ya koi bhi LLM** ko MCP tools ke sath use kar rahe ho production mein, toh:

1. **Auth check karo** - Kaunsa tenant call kar raha hai?
2. **Permission check karo** - Uske paas uska access hai?
3. **Rate limit check karo** - Quota exhaust ho gaya?
4. **Tool call karo** - mcp-resilient automatically retry/fallback/monitor karega

Yeh guide exact same pattern dikhata hai! 👇

---

## 🎯 Why You MUST Use mcp-resilient in Production

### Problem: AI Agents ko Tool Calls Fail Hote Hain

```
LLM: "Call threat_intel for example.com"
Tool: Returns 500 error
LLM: "Uhmm... now what?"  ← Bad situation
```

### Solution: mcp-resilient Handles It Automatically

```
LLM: "Call threat_intel for example.com"
Call 1: Fails (timeout)
       → Retry with exponential backoff
Call 2: Fails (rate limited)
       → Wait, then retry
Call 3: Success! ✓
       → Return result to LLM
       → Log metrics
       → Track cost
```

---

## 📋 Production Checklist

### Before Deploy:
- [ ] Auth provider connected (OAuth, SAML, API keys)
- [ ] Rate limits configured per tenant
- [ ] Circuit breaker thresholds set ($cost budget)
- [ ] Monitoring/alerting setup (Prometheus, Datadog)
- [ ] Error handling patterns tested
- [ ] Fallback tools configured
- [ ] Load testing completed

### After Deploy:
- [ ] Monitor circuit breaker state
- [ ] Watch rate limit exhaustion
- [ ] Track cost per tenant
- [ ] Alert on permission denied
- [ ] Review retry patterns
- [ ] Tune backoff strategy

---

## 🔒 Security Best Practices

### 1. Token Management
```python
❌ WRONG: config = ReliabilityConfig(tool_name="threat_intel", token="sk_12345")
✅ RIGHT: token = os.getenv("LLM_API_KEY")  # From env/vault
```

### 2. Permission Matrix
```python
✅ Setup role-based access:
   - premium_tier: Can call all tools
   - basic_tier: Limited tool access
   - free_tier: Only read-only tools
```

### 3. Rate Limiting
```python
✅ Different limits per tenant:
   - Enterprise: 1000 calls/min
   - Premium: 100 calls/min
   - Free: 10 calls/min
```

### 4. Secrets in Vault (NOT in code)
```python
✅ Use:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Environment variables

❌ Don't hardcode tokens in code!
```

---

## 🏗️ Architecture for AI Agents

```
┌─────────────────────────────────────┐
│         Claude / GPT / LLM          │
└──────────────────┬──────────────────┘
                   │
                   ↓
        ┌──────────────────────┐
        │   MCP Protocol       │
        │  (Tool Discovery)    │
        └──────────────┬───────┘
                       │
                       ↓
        ┌──────────────────────────────┐
        │  AI Agent Framework          │
        │  (Your Application)          │
        └──────────────┬───────────────┘
                       │
                       ↓
        ┌──────────────────────────────────────┐
        │  safe_tool_call()                    │
        │  ├─ Validate token (Auth)            │
        │  ├─ Check permission                 │
        │  ├─ Check rate limit                 │
        │  └─ Call @mcp_reliable decorator     │
        └──────────────┬───────────────────────┘
                       │
                       ↓
        ┌──────────────────────────────────┐
        │   @mcp_reliable decorator        │
        │   ├─ Retry on failure            │
        │   ├─ Circuit breaker             │
        │   ├─ Fallback to backup tools    │
        │   └─ Track metrics               │
        └──────────────┬────────────────────┘
                       │
                       ↓
        ┌──────────────────────────────────┐
        │  Actual Tool Call                │
        │  (threat_intel, email_verify,   │
        │   database query, API call)      │
        └──────────────────────────────────┘
```

---

## 💻 Integration Steps

### Step 1: Install Package
```bash
pip install mcp-resilient
```

### Step 2: Setup Configuration (like in the demo)
```python
from mcp_resilient import ReliabilityConfig, mcp_reliable

config = ReliabilityConfig(
    tool_name="threat_intel",
    auth={"enabled": True, "provider": "static"},
    rate_limit={"enabled": True, "default_capacity": 100}
)
```

### Step 3: Create Decorated Tool
```python
@mcp_reliable(config)
async def call_threat_intel(ioc: str, tool_name: str = "threat_intel"):
    # Your MCP client call here
    return await mcp_client.call_tool(tool_name, {"ioc": ioc})
```

### Step 4: Add Safety Wrapper (MOST IMPORTANT)
```python
async def safe_tool_call(ioc: str, token: str):
    # 1. Validate token
    tenant = await auth.validate_token(token)
    
    # 2. Check permission
    if not await auth.check_permission(tenant, "threat_intel", "execute"):
        raise PermissionDenied(...)
    
    # 3. Check rate limit
    if not rate_limiter.try_acquire(tenant):
        raise RateLimitExceeded(...)
    
    # 4. Safe to call!
    return await call_threat_intel(ioc, tool_name="threat_intel")
```

### Step 5: Use in LLM Framework
```python
# In your Claude client handler:
async def handle_tool_call(tool_name, tool_input, user_token):
    if tool_name == "threat_intel":
        return await safe_tool_call(tool_input["ioc"], user_token)
    # More tools...
```

---

## 📊 Monitoring & Observability

### What to Monitor

```python
✅ SUCCESS METRICS:
   - Avg response time (track latency increase)
   - Success rate (should be 99%+)
   - Retry count (high = tool is flaky)

✅ FAILURE METRICS:
   - Circuit breaker trips (alert at 10+/hour)
   - Rate limit hits (normal, but track per tenant)
   - Permission denied (investigate if spike)

✅ COST METRICS:
   - Total API spend per day
   - Spend per tenant
   - Spend per tool
   - Overage alerts if near budget
```

### Export to Prometheus

```python
config = ReliabilityConfig(
    tool_name="threat_intel",
    observability={
        "enabled": True,
        "exporter": "prometheus",  # ← Automatic export
        "log_level": "INFO"
    }
)
```

### Query Examples (Prometheus)

```promql
# P95 latency for threat_intel
histogram_quantile(0.95, rate(mcp_call_duration_seconds_bucket{tool="threat_intel"}[5m]))

# Circuit breaker trip rate
rate(mcp_circuit_open_total[5m])

# Cost per tenant
sum by (tenant) (rate(mcp_tool_cost_total[1d]))
```

---

## 🚨 Error Handling Patterns

### Pattern 1: Graceful Degradation
```python
try:
    result = await safe_tool_call(ioc, token)
except CircuitOpenError:
    # Tool is broken, use cached result
    return cache.get(ioc) or "Unable to check threat level"
except RateLimitExceeded:
    # Quota exhausted, tell user to retry later
    return "Rate limit hit. Please retry after 30 seconds"
```

### Pattern 2: Fallback Chain
```python
config = ReliabilityConfig(
    tool_name="threat_intel_primary",
    fallback={
        "enabled": True,
        "tool_chain": [
            "threat_intel_backup",      # Try backup
            "threat_intel_cached",       # Use cache
            "threat_intel_default"       # Safe default
        ]
    }
)
```

### Pattern 3: Alert on Auth Failures
```python
except InvalidTokenError:
    # Token expired - tell user to re-authenticate
    logger.warning(f"Invalid token for user {user_id}")
    # Send alert: "Auth issue detected"
    
except PermissionDeniedError:
    # User trying to access tool they don't have access to
    logger.warning(f"Permission denied for {tenant} on {tool}")
    # Send alert: "Possible unauthorized access attempt"
```

---

## 🎓 Real-World Scenario

### Scenario: AI Agent Analyzing Malware

```
User: "Is this URL malicious?"
      ↓
LLM: "I'll check with threat_intel tool"
      ↓
Your Framework:
  1. Get user's auth token from session
  2. Call safe_tool_call(url, token)
      ↓
Auth Layer:
  3. Validate token (✓ valid)
  4. Check permission (✓ allowed)
  5. Check rate limit (✓ under quota)
      ↓
mcp-resilient:
  6. Call threat_intel
  7. If fails → Retry (up to 3x)
  8. If all fail → Try fallback tools
  9. If circuit open → Return cached result
  10. Track metrics
      ↓
Result:
  11. Return to LLM: "Yes, malicious, 95% confidence"
  12. LLM formulates response to user
```

---

## 📝 Configuration Examples

### Example 1: Conservative (Cost-Conscious)
```yaml
tool_name: threat_intel
retry:
  max_attempts: 2              # Minimal retries
  backoff:
    strategy: fixed
    base_delay: 0.5
circuit_breaker:
  cost_budget: 5.0             # $5/day limit
rate_limit:
  default_capacity: 10         # Few calls
  default_refill_rate: 1.0
```

### Example 2: Aggressive (High-Reliability)
```yaml
tool_name: threat_intel
retry:
  max_attempts: 5              # More retries
  backoff:
    strategy: exponential
    base_delay: 1.0
    max_delay: 120.0
circuit_breaker:
  cost_budget: 100.0           # $100/day limit
rate_limit:
  default_capacity: 1000       # Many calls
  default_refill_rate: 100.0
```

### Example 3: Multi-Tenant
```yaml
tool_name: threat_intel
auth:
  enabled: true
  provider: static
rate_limit:
  enabled: true
  default_capacity: 50
# Per-tenant overrides:
# acme_corp: capacity=1000, rate=100
# widget_co: capacity=10, rate=1
```

---

## ✅ Go-Live Checklist

```
WEEK 1:
  [ ] Load demo file (production_ai_agent_setup.py)
  [ ] Customize for your MCP tools
  [ ] Setup auth provider
  [ ] Configure rate limits per tenant
  
WEEK 2:
  [ ] Integration testing with real LLM
  [ ] Load testing (1000 concurrent users)
  [ ] Circuit breaker testing
  [ ] Fallback chain testing
  
WEEK 3:
  [ ] Prometheus setup
  [ ] Alert configuration
  [ ] Runbook documentation
  [ ] Team training
  
DEPLOY:
  [ ] Canary deployment (5% traffic)
  [ ] Monitor metrics 24/7
  [ ] Alert on any circuit breaks
  [ ] Gradual rollout to 100%
```

---

## 🆘 Troubleshooting

### Q: Circuit breaker keeps opening
```
A: 1. Check upstream tool health
   2. Review failure threshold (too aggressive?)
   3. Increase cooldown time
   4. Check logs for actual error
```

### Q: Rate limit errors for good users
```
A: 1. Audit their actual usage
   2. Increase their quota
   3. Check for bot traffic
   4. Add better backoff strategy
```

### Q: Tokens expiring too fast
```
A: 1. Extend token TTL
   2. Implement token refresh
   3. Use long-lived API keys instead
   4. Consider JWT with refresh tokens
```

### Q: High latency on retries
```
A: 1. Reduce max_attempts (retrying is expensive)
   2. Increase base_delay to avoid overwhelming
   3. Check upstream service health
   4. Add caching layer
```

---

## 🔗 Links & Resources

- **Main Repo:** See your local copy
- **Examples:** `examples/production_ai_agent_setup.py`
- **Auth Patterns:** `examples/MULTITENANT_GUIDE.md`
- **Config Schema:** `src/mcp_resilient/core/config.py`
- **All Exceptions:** `src/mcp_resilient/core/exceptions.py`

---

## 🚀 You're Ready!

**Next step:** Copy `production_ai_agent_setup.py` and customize it for your tools!

Happy deploying! 🎉
