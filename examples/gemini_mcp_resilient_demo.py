"""
Real-time integration demo: mcp-resilient + Gemini API (Function Calling).

This script demonstrates how to wrap a function-calling tool using the mcp-resilient
decorator to handle transient errors, making LLM-driven tool executions robust.

Prerequisites:
    1. Install the Gemini SDK:
       pip install google-genai
    2. Set your Gemini API key:
       Windows (PowerShell): $env:GEMINI_API_KEY="your-key-here"
       Windows (CMD): set GEMINI_API_KEY=your-key-here
       Linux/macOS: export GEMINI_API_KEY="your-key-here"
"""

import asyncio
import os
import sys

# Ensure mcp-resilient is importable even if run from this examples/ folder directly
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: The 'google-genai' package is not installed.")
    print("Please install it using: pip install google-genai")
    sys.exit(1)

from mcp_resilient import ReliabilityConfig, RetryConfig, mcp_reliable

# 1. Define the reliability config
config = ReliabilityConfig(
    tool_name="get_cyber_intel",
    retry=RetryConfig(
        max_attempts=3,
        # Use a short base delay for demonstration purposes
        backoff={"strategy": "fixed", "base_delay": 0.5},
    ),
)

# Keep track of calls to show retries in action
call_count = 0


# 2. Decorate the tool with @mcp_reliable
@mcp_reliable(config)
async def get_cyber_intel(domain: str) -> str:
    """
    Retrieve cybersecurity threat intelligence for a given domain.

    Args:
        domain: The domain name to inspect (e.g. 'malicious-site.com').
    """
    global call_count
    call_count += 1
    print(f"\n[Tool Execution] Attempt #{call_count} for domain: {domain}")

    # Simulate flaky behavior: fail on first 2 calls, succeed on the 3rd
    if call_count < 3:
        print(
            f"[Tool Execution] Simulating transient network failure (Attempt {call_count})..."
        )
        raise ConnectionError("Connection reset by peer (simulated transient error)")

    print("[Tool Execution] Success! Returning threat score.")
    return f"Threat report for {domain}: Threat level is HIGH. Known distribution point for malware."


async def run_demo():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Please set it in your terminal:")
        print('  Windows (PowerShell): $env:GEMINI_API_KEY="your_key"')
        sys.exit(1)

    print("Initializing Gemini Client...")
    # Client will automatically load GEMINI_API_KEY from environment
    client = genai.Client()

    prompt = "Check if the domain 'unsafe-site.xyz' is malicious using the get_cyber_intel tool."
    print(f"\nSending prompt to Gemini: '{prompt}'")

    print(
        "Calling Gemini with automatic function calling (mcp-resilient handles retries)..."
    )
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[get_cyber_intel],
            ),
        )
        print(f"\n[Gemini] Final Response:\n{response.text}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(run_demo())
