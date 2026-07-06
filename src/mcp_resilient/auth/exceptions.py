"""Auth-specific exceptions."""

from mcp_resilient.core.exceptions import MCPResilientError


class AuthError(MCPResilientError):
    """Base auth exception."""

    pass


class InvalidTokenError(AuthError):
    """Raised when token is invalid or expired."""

    def __init__(self, reason: str = "Invalid token"):
        super().__init__(reason)


class PermissionDeniedError(AuthError):
    """Raised when tenant lacks required permission."""

    def __init__(self, tenant_id: str, tool_name: str, action: str):
        super().__init__(
            f"Tenant '{tenant_id}' denied access to tool '{tool_name}' for action '{action}'"
        )


class RateLimitExceededError(AuthError):
    """Raised when tenant exceeds rate limit."""

    def __init__(self, tenant_id: str, retry_after: float = 1.0):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for tenant '{tenant_id}'. Retry after {retry_after:.1f}s")
