"""Authentication and authorization module for multi-tenant support."""

from mcp_resilient.auth.exceptions import (
    AuthError,
    InvalidTokenError,
    PermissionDeniedError,
    RateLimitExceededError,
)
from mcp_resilient.auth.provider import (
    AuthContext,
    AuthProvider,
    NoAuthProvider,
    StaticTokenAuthProvider,
)

__all__ = [
    "AuthProvider",
    "StaticTokenAuthProvider",
    "NoAuthProvider",
    "AuthContext",
    "AuthError",
    "InvalidTokenError",
    "PermissionDeniedError",
    "RateLimitExceededError",
]
