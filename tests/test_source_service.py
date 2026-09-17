"""Unit and error-path tests for resilient source wrappers."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from ai import Source
from ai.providers.base import ProviderError

from researcher.config import Settings
from researcher.models import SourceName
from researcher.services.source_service import SourceService
from researcher.storage.memory import MemoryRepository


def settings(**updates: Any) -> Settings:
    return Settings(
        storage_backend="memory",
        arxiv_min_interval_seconds=0,
        retry_min_wait_seconds=0,
        retry_max_wait_seconds=0,
        **updates,
    )


async def test_fetch_populates_and_reuses_cache() -> None:
    calls = 0

    async def fake_fetcher(question: str, **_: Any) -> list[Source]:
        nonlocal calls
        calls += 1
        return [Source(title=question, url="https://x.test", snippet="s", origin="web")]

    repository = MemoryRepository()
    service = SourceService(settings(), repository, fetchers={SourceName.WEB: fake_fetcher})
    async with httpx.AsyncClient() as client:
        first = await service.fetch(SourceName.WEB, "Question", no_cache=False, client=client)
        second = await service.fetch(SourceName.WEB, " question ", no_cache=False, client=client)
    assert calls == 1
    assert first.cache_hit is False
    assert second.cache_hit is True


async def test_no_cache_bypasses_reads_and_writes() -> None:
    calls = 0

    async def fake_fetcher(question: str, **_: Any) -> list[Source]:
        nonlocal calls
        calls += 1
        return [Source(title=question, url=f"https://x.test/{calls}", snippet="s", origin="web")]

    repository = MemoryRepository()
    service = SourceService(settings(), repository, fetchers={SourceName.WEB: fake_fetcher})
    async with httpx.AsyncClient() as client:
        await service.fetch(SourceName.WEB, "q", no_cache=True, client=client)
        await service.fetch(SourceName.WEB, "q", no_cache=True, client=client)
    assert calls == 2
    assert repository.cache == {}


async def test_transient_provider_error_is_retried() -> None:
    calls = 0

    async def flaky(question: str, **_: Any) -> list[Source]:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ProviderError("temporary")
        return [Source(title=question, url="https://x.test", snippet="s", origin="web")]

    repository = MemoryRepository()
    service = SourceService(
        settings(max_retry_attempts=3),
        repository,
        fetchers={SourceName.WEB: flaky},
    )
    async with httpx.AsyncClient() as client:
        result = await service.fetch(SourceName.WEB, "q", no_cache=True, client=client)
    assert calls == 3
    assert len(result.sources) == 1


async def test_timeout_is_retried_then_raised() -> None:
    async def slow(question: str, **_: Any) -> list[Source]:
        await asyncio.sleep(0.05)
        return []

    repository = MemoryRepository()
    service = SourceService(
        settings(max_retry_attempts=2, per_source_timeout_seconds=0.005),
        repository,
        fetchers={SourceName.WEB: slow},
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(TimeoutError):
            await service.fetch(SourceName.WEB, "q", no_cache=True, client=client)
