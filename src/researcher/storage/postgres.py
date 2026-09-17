"""PostgreSQL persistence implemented with an asyncpg connection pool."""

from __future__ import annotations

import json
from typing import Any

import asyncpg
from ai import Source

from researcher.errors import StorageError
from researcher.models import ResearchResult, SourceName
from researcher.storage.base import ResearchRepository

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS source_cache (
    source TEXT NOT NULL,
    query_key TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (source, query_key)
);

CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    requested_sources TEXT[] NOT NULL,
    answer TEXT NOT NULL,
    warnings JSONB NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    duration_ms DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS research_sources (
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    origin TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    snippet TEXT NOT NULL,
    PRIMARY KEY (session_id, ordinal)
);

CREATE TABLE IF NOT EXISTS source_attempts (
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    cache_hit BOOLEAN NOT NULL,
    duration_ms DOUBLE PRECISION NOT NULL,
    error TEXT,
    result_count INTEGER NOT NULL,
    PRIMARY KEY (session_id, source)
);

CREATE TABLE IF NOT EXISTS citations (
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    citation_index INTEGER NOT NULL,
    source_ordinal INTEGER NOT NULL,
    PRIMARY KEY (session_id, citation_index),
    FOREIGN KEY (session_id, source_ordinal)
        REFERENCES research_sources(session_id, ordinal) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_source_cache_expiry ON source_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_research_sessions_created ON research_sessions(created_at);
"""


class PostgresRepository(ResearchRepository):
    """Store cache entries and research audit records in PostgreSQL."""

    def __init__(self, database_url: str, *, min_size: int = 1, max_size: int = 5) -> None:
        self._database_url = database_url
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """Connect and create idempotent database structures."""
        try:
            self._pool = await asyncpg.create_pool(
                dsn=self._database_url,
                min_size=self._min_size,
                max_size=self._max_size,
                command_timeout=15,
            )
            async with self._pool.acquire() as connection:
                await connection.execute(_SCHEMA_SQL)
        except (asyncpg.PostgresError, OSError, TimeoutError) as exc:
            raise StorageError(f"PostgreSQL initialization failed: {exc}") from exc

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise StorageError("PostgreSQL repository has not been initialized")
        return self._pool

    async def get_cached_sources(self, source: SourceName, query_key: str) -> list[Source] | None:
        """Read a live cache entry and lazily remove expired rows."""
        pool = self._require_pool()
        try:
            await pool.execute(
                """
                DELETE FROM source_cache
                WHERE source = $1 AND query_key = $2 AND expires_at <= NOW();
                """,
                source.value,
                query_key,
            )
            row = await pool.fetchrow(
                """
                SELECT payload FROM source_cache
                WHERE source = $1 AND query_key = $2 AND expires_at > NOW()
                """,
                source.value,
                query_key,
            )
            if row is None:
                return None
            payload: Any = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            return [Source.model_validate(item) for item in payload]
        except (asyncpg.PostgresError, ValueError, TypeError) as exc:
            raise StorageError(f"Cache read failed for {source.value}: {exc}") from exc

    async def put_cached_sources(
        self,
        source: SourceName,
        query_key: str,
        sources: list[Source],
        ttl_seconds: int,
    ) -> None:
        """Upsert a TTL cache entry."""
        pool = self._require_pool()
        payload = json.dumps([item.model_dump(mode="json") for item in sources])
        try:
            await pool.execute(
                """
                INSERT INTO source_cache(source, query_key, payload, expires_at)
                VALUES($1, $2, $3::jsonb, NOW() + ($4 * INTERVAL '1 second'))
                ON CONFLICT(source, query_key) DO UPDATE SET
                    payload = EXCLUDED.payload,
                    created_at = NOW(),
                    expires_at = EXCLUDED.expires_at
                """,
                source.value,
                query_key,
                payload,
                ttl_seconds,
            )
        except asyncpg.PostgresError as exc:
            raise StorageError(f"Cache write failed for {source.value}: {exc}") from exc

    async def save_result(self, result: ResearchResult) -> None:
        """Persist a session, source attempts and citations in one transaction."""
        pool = self._require_pool()
        sources = result.retrieved_sources
        source_ordinals = {
            (source.origin, source.url): index for index, source in enumerate(sources, start=1)
        }
        try:
            async with pool.acquire() as connection, connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO research_sessions(
                        id, question, requested_sources, answer, warnings,
                        started_at, duration_ms
                    ) VALUES($1, $2, $3, $4, $5::jsonb, $6, $7)
                    """,
                    result.session_id,
                    result.question,
                    [source.value for source in result.requested_sources],
                    result.answer.answer,
                    json.dumps(result.warnings),
                    result.started_at,
                    result.duration_ms,
                )
                await connection.executemany(
                    """
                    INSERT INTO research_sources(
                        session_id, ordinal, origin, title, url, snippet
                    ) VALUES($1, $2, $3, $4, $5, $6)
                    """,
                    [
                        (
                            result.session_id,
                            index,
                            source.origin,
                            source.title,
                            source.url,
                            source.snippet,
                        )
                        for index, source in enumerate(sources, start=1)
                    ],
                )
                await connection.executemany(
                    """
                    INSERT INTO source_attempts(
                        session_id, source, cache_hit, duration_ms, error, result_count
                    ) VALUES($1, $2, $3, $4, $5, $6)
                    """,
                    [
                        (
                            result.session_id,
                            fetch.source.value,
                            fetch.cache_hit,
                            fetch.duration_ms,
                            fetch.error,
                            len(fetch.sources),
                        )
                        for fetch in result.fetches
                    ],
                )
                citation_rows = []
                for citation in result.answer.citations:
                    ordinal = source_ordinals.get((citation.source.origin, citation.source.url))
                    if ordinal is not None:
                        citation_rows.append((result.session_id, citation.index, ordinal))
                if citation_rows:
                    await connection.executemany(
                        """
                        INSERT INTO citations(session_id, citation_index, source_ordinal)
                        VALUES($1, $2, $3)
                        """,
                        citation_rows,
                    )
        except asyncpg.PostgresError as exc:
            raise StorageError(f"Saving research session failed: {exc}") from exc

    async def close(self) -> None:
        """Close the connection pool if it was opened."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
