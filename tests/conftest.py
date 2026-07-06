from __future__ import annotations

import pytest

from mcp_resilient.storage.memory_store import InMemoryStateStore


@pytest.fixture
def memory_store() -> InMemoryStateStore:
    return InMemoryStateStore()
