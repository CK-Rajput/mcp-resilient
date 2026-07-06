"""Authentication and authorization layer for multi-tenant access control."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class AuthProvider(ABC):
    """Abstract base for authentication providers."""

    @abstractmethod
    async def validate_token(self, token: str) -> Optional[dict[str, Any]]:
        """Validate token and return tenant context if valid.
        
        Returns:
            Dict with tenant_id, permissions, etc. if valid, None otherwise.
        """
        pass

    @abstractmethod
    async def check_permission(self, tenant_id: str, tool_name: str, action: str) -> bool:
        """Check if tenant has permission for action on tool.
        
        Args:
            tenant_id: Tenant identifier
            tool_name: Tool being accessed
            action: Action (read, execute, admin)
        
        Returns:
            True if permitted, False otherwise.
        """
        pass


class StaticTokenAuthProvider(AuthProvider):
    """Simple in-memory auth provider for testing/demo."""

    def __init__(self):
        # Format: token -> {tenant_id, permissions}
        self.tokens: dict[str, dict[str, Any]] = {}
        self.permissions: dict[tuple[str, str, str], bool] = {}

    def register_token(
        self, token: str, tenant_id: str, permissions: list[str] | None = None
    ) -> None:
        """Register a valid token for a tenant."""
        self.tokens[token] = {
            "tenant_id": tenant_id,
            "permissions": permissions or ["execute"],
        }

    def set_permission(self, tenant_id: str, tool_name: str, action: str, allowed: bool) -> None:
        """Set permission for tenant+tool+action."""
        self.permissions[(tenant_id, tool_name, action)] = allowed

    async def validate_token(self, token: str) -> Optional[dict[str, Any]]:
        """Return tenant context if token valid."""
        return self.tokens.get(token)

    async def check_permission(self, tenant_id: str, tool_name: str, action: str) -> bool:
        """Check permission in simple lookup."""
        key = (tenant_id, tool_name, action)
        # Default: allow if not explicitly denied
        return self.permissions.get(key, True)


class NoAuthProvider(AuthProvider):
    """No-op auth provider for backward compatibility."""

    async def validate_token(self, token: str) -> Optional[dict[str, Any]]:
        """Always accept any token as tenant 'default'."""
        return {"tenant_id": "default", "permissions": ["execute"]}

    async def check_permission(self, tenant_id: str, tool_name: str, action: str) -> bool:
        """Always allow."""
        return True


class AuthContext:
    """Current authentication context for a request."""

    def __init__(self, tenant_id: str, token: str, metadata: dict[str, Any] | None = None):
        self.tenant_id = tenant_id
        self.token = token
        self.metadata = metadata or {}

    def has_permission(self, action: str) -> bool:
        """Check if tenant has permission."""
        perms = self.metadata.get("permissions", [])
        return action in perms or "admin" in perms
