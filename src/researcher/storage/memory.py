"""Fast repository used by offline demos and tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ai import Source

from researcher.models import ResearchResult, SourceName
from researcher.storage.base import ResearchRepository


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    sources: list[Source]
    expires_at: datetime


class MemoryRepository(ResearchRepository):
    """In-memory implementation with the same semantics as PostgreSQL."""

    def __init__(self) -> None:
        self.cache: dict[tuple[SourceName, str], _CacheEntry] = {}
        self.results: list[ResearchResult] = []

    async def initialize(self) -> None:
        """Memory storage requires no initialization."""

    async def get_cached_sources(self, source: SourceName, query_key: str) -> list[Source] | None:
        """Return a copy of a live entry and evict expired entries."""
        key = (source, query_key)
        entry = self.cache.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(UTC):
            self.cache.pop(key, None)
            return None
        return list(entry.sources)

    async def put_cached_sources(
        self,
        source: SourceName,
        query_key: str,
        sources: list[Source],
        ttl_seconds: int,
    ) -> None:
        """Store a defensive copy of a cache result."""
        self.cache[(source, query_key)] = _CacheEntry(
            sources=list(sources),
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )

    async def save_result(self, result: ResearchResult) -> None:
        """Keep the completed result for assertions and offline inspection."""
        self.results.append(result.model_copy(deep=True))

    async def close(self) -> None:
        """Memory storage holds no external resources."""
