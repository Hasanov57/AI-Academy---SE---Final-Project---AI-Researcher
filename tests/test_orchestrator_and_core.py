"""Concurrency, graceful-degradation and happy-path integration tests."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
from ai import Source
from ai.providers.base import ProviderError

from researcher.concurrency.orchestrator import SourceOrchestrator
from researcher.config import Settings
from researcher.core.researcher import Researcher
from researcher.errors import NoSourcesError
from researcher.models import ResearchRequest, SourceName
from researcher.offline import OfflineLLM
from researcher.services.source_service import SourceService
from researcher.services.synthesis_service import SynthesisService
from researcher.storage.memory import MemoryRepository


def make_settings(**updates: Any) -> Settings:
    return Settings(
        storage_backend="memory",
        arxiv_min_interval_seconds=0,
        retry_min_wait_seconds=0,
        retry_max_wait_seconds=0,
        max_retry_attempts=1,
        **updates,
    )


def source(origin: str, suffix: str) -> Source:
    return Source(
        title=f"Source {suffix}",
        url=f"https://example.com/{suffix}",
        snippet="Useful evidence",
        origin=origin,
    )


async def test_concurrent_fetch_is_faster_than_sequential() -> None:
    active = 0
    peak_active = 0

    async def delayed(_: str, **kwargs: Any) -> list[Source]:
        nonlocal active, peak_active
        del kwargs
        active += 1
        peak_active = max(peak_active, active)
        await asyncio.sleep(0.04)
        active -= 1
        return [source("web", str(time.perf_counter()))]

    settings = make_settings()
    repository = MemoryRepository()
    service = SourceService(
        settings,
        repository,
        fetchers={item: delayed for item in SourceName},
    )
    orchestrator = SourceOrchestrator(settings, service)
    selected = tuple(SourceName)
    started = time.perf_counter()
    await orchestrator.fetch_all("q", selected, no_cache=True, concurrent=False)
    sequential = time.perf_counter() - started
    started = time.perf_counter()
    await orchestrator.fetch_all("q", selected, no_cache=True, concurrent=True)
    concurrent = time.perf_counter() - started
    assert concurrent < sequential
    assert peak_active == 3


async def test_one_source_failure_degrades_gracefully() -> None:
    async def good(_: str, **kwargs: Any) -> list[Source]:
        del kwargs
        return [source("wikipedia", "wiki")]

    async def bad(_: str, **kwargs: Any) -> list[Source]:
        del kwargs
        raise ProviderError("arXiv unavailable")

    settings = make_settings()
    repository = MemoryRepository()
    service = SourceService(
        settings,
        repository,
        fetchers={
            SourceName.WIKIPEDIA: good,
            SourceName.ARXIV: bad,
        },
    )
    orchestrator = SourceOrchestrator(settings, service)
    outcomes = await orchestrator.fetch_all(
        "q", (SourceName.WIKIPEDIA, SourceName.ARXIV), no_cache=True
    )
    assert outcomes[0].succeeded
    assert outcomes[1].error == "arXiv unavailable"


async def test_shared_client_is_identifiable_and_follows_redirects() -> None:
    observed: dict[str, object] = {}

    async def inspect_client(_: str, **kwargs: Any) -> list[Source]:
        client = kwargs["client"]
        observed["follow_redirects"] = client.follow_redirects
        observed["user_agent"] = client.headers["User-Agent"]
        return [source("wikipedia", "client")]

    settings = make_settings(http_user_agent="CourseResearcher/1.0")
    repository = MemoryRepository()
    service = SourceService(
        settings,
        repository,
        fetchers={SourceName.WIKIPEDIA: inspect_client},
    )
    orchestrator = SourceOrchestrator(settings, service)
    await orchestrator.fetch_all("q", (SourceName.WIKIPEDIA,), no_cache=True)
    assert observed == {
        "follow_redirects": True,
        "user_agent": "CourseResearcher/1.0",
    }


async def test_researcher_happy_path_persists_result() -> None:
    async def wiki(_: str, **kwargs: Any) -> list[Source]:
        del kwargs
        return [source("wikipedia", "wiki")]

    settings = make_settings()
    repository = MemoryRepository()
    source_service = SourceService(settings, repository, fetchers={SourceName.WIKIPEDIA: wiki})
    researcher = Researcher(
        SourceOrchestrator(settings, source_service),
        SynthesisService(settings, llm=OfflineLLM()),
        repository,
    )
    result = await researcher.ask(
        ResearchRequest(question="What is the evidence?", sources=(SourceName.WIKIPEDIA,))
    )
    assert result.answer.citations
    assert repository.results[0].session_id == result.session_id


async def test_researcher_rejects_all_empty_sources() -> None:
    async def empty(_: str, **kwargs: Any) -> list[Source]:
        del kwargs
        return []

    settings = make_settings()
    repository = MemoryRepository()
    service = SourceService(settings, repository, fetchers={SourceName.WEB: empty})
    researcher = Researcher(
        SourceOrchestrator(settings, service),
        SynthesisService(settings, llm=OfflineLLM()),
        repository,
    )
    with pytest.raises(NoSourcesError):
        await researcher.ask(ResearchRequest(question="Q", sources=(SourceName.WEB,)))
