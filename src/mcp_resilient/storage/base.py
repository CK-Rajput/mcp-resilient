from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StateStore(ABC):
    """Abstract key-value backend for circuit breaker state.

    Implement this to plug in any backend — memory (default), Redis
    (bundled), DynamoDB, etcd, whatever your deployment already runs.
    """

    @abstractmethod
    async def get(self, key: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def set(self, key: str, value: dict[str, Any]) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...
