"""Offline database boundary tests; real database checks live in scripts/."""

from unittest.mock import AsyncMock

import asyncpg
import pytest

from researcher.errors import StorageError
from researcher.models import SourceName
from researcher.storage.postgres import PostgresRepository


async def test_uninitialized_repository_has_clear_error() -> None:
    repository = PostgresRepository("postgresql://unused")
    with pytest.raises(StorageError, match="not been initialized"):
        await repository.get_cached_sources(SourceName.WEB, "q")


async def test_database_connection_failure_is_wrapped(monkeypatch) -> None:
    monkeypatch.setattr(asyncpg, "create_pool", AsyncMock(side_effect=OSError("offline")))
    repository = PostgresRepository("postgresql://unused")
    with pytest.raises(StorageError, match="initialization failed"):
        await repository.initialize()


async def test_corrupt_cached_payload_is_rejected() -> None:
    repository = PostgresRepository("postgresql://unused")
    repository._pool = AsyncMock()
    repository._pool.fetchrow.return_value = {"payload": "invalid JSON"}
    with pytest.raises(StorageError, match="Cache read failed"):
        await repository.get_cached_sources(SourceName.WEB, "q")


async def test_database_write_failure_is_wrapped() -> None:
    repository = PostgresRepository("postgresql://unused")
    repository._pool = AsyncMock()
    repository._pool.execute.side_effect = asyncpg.PostgresError("connection failed")
    with pytest.raises(StorageError, match="Cache write failed"):
        await repository.put_cached_sources(SourceName.WEB, "q", [], 30)
