"""Repository abstraction owned by the student software layer."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai import Source

from researcher.models import ResearchResult, SourceName


class ResearchRepository(ABC):
    """Abstract persistence boundary for cache and completed research sessions."""

    @abstractmethod
    async def initialize(self) -> None:
        """Create required storage structures if they do not exist."""

    @abstractmethod
    async def get_cached_sources(self, source: SourceName, query_key: str) -> list[Source] | None:
        """Return a non-expired cache entry, or ``None`` on a miss."""

    @abstractmethod
    async def put_cached_sources(
        self,
        source: SourceName,
        query_key: str,
        sources: list[Source],
        ttl_seconds: int,
    ) -> None:
        """Persist a source result with its expiration time."""

    @abstractmethod
    async def save_result(self, result: ResearchResult) -> None:
        """Persist a completed research session atomically."""

    @abstractmethod
    async def close(self) -> None:
        """Release any held resources."""
