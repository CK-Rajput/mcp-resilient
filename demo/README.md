# Your AI Agent Production Setup

This directory contains your customized production setup for mcp-resilient.

## Quick Start

### Step 1: Setup Environment
```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your actual values
nano .env  # or vim/code
```

### Step 2: Install Dependencies
```bash
pip install mcp-resilient
```

### Step 3: Run Demo
```bash
python ai_agent_setup.py
```

### Step 4: Customize for Your Tools

In `ai_agent_setup.py`:

1. Replace `"threat_intel"` with your actual tool names
2. Update `setup_auth_provider()` to connect with your auth service
3. Replace mock API calls with real MCP client calls
4. Update `create_reliability_config()` with your requirements

### Step 5: Deploy to Production

- Load `.env` from secure vault (AWS Secrets, HashiCorp Vault, etc)
- Connect Prometheus monitoring
- Set up alerting for circuit breaker events
- Run load tests before deploying

## Files

- **ai_agent_setup.py** - Your production setup (EDIT THIS)
- **.env.example** - Environment variables template
- **.env** - Your actual secrets (NEVER commit this!)

## Security

⚠️ **IMPORTANT:**
- Never commit `.env` to git
- Use `.env.example` as template only
- Load secrets from vault in production
- Rotate API tokens regularly

## Monitoring

Once deployed:

```bash
# Check Prometheus metrics
curl http://localhost:8000/metrics

# Monitor circuit breaker state
curl http://localhost:8000/metrics | grep circuit

# Monitor rate limits
curl http://localhost:8000/metrics | grep rate_limit
```

## Troubleshooting

See `../docs/PRODUCTION_GUIDE.md` for common issues and solutions.
