"""Repository contract tests using the network-free memory implementation."""

from __future__ import annotations

from ai import AnswerWithCitations, Citation, Source

from researcher.models import ResearchResult, SourceFetchOutcome, SourceName
from researcher.storage.memory import MemoryRepository


def make_source() -> Source:
    return Source(title="Paper", url="https://example.com/paper", snippet="Evidence", origin="web")


async def test_memory_cache_round_trip() -> None:
    repository = MemoryRepository()
    source = make_source()
    await repository.put_cached_sources(SourceName.WEB, "query", [source], 60)
    assert await repository.get_cached_sources(SourceName.WEB, "query") == [source]


async def test_memory_cache_expires_zero_ttl() -> None:
    repository = MemoryRepository()
    await repository.put_cached_sources(SourceName.WEB, "query", [make_source()], 0)
    assert await repository.get_cached_sources(SourceName.WEB, "query") is None


async def test_memory_cache_miss_returns_none() -> None:
    repository = MemoryRepository()
    assert await repository.get_cached_sources(SourceName.ARXIV, "missing") is None


async def test_memory_repository_saves_defensive_copy() -> None:
    repository = MemoryRepository()
    source = make_source()
    duplicate = Source(
        title="Duplicate provider hit",
        url="https://example.com/paper?utm_source=duplicate",
        snippet="The same evidence",
        origin="wikipedia",
    )
    result = ResearchResult(
        question="Question?",
        requested_sources=(SourceName.WEB,),
        answer=AnswerWithCitations(
            question="Question?",
            answer="Answer [1].",
            citations=[Citation(index=1, source=source)],
        ),
        fetches=[
            SourceFetchOutcome(source=SourceName.WEB, sources=[source], duration_ms=1),
            SourceFetchOutcome(
                source=SourceName.WIKIPEDIA,
                sources=[duplicate],
                duration_ms=1,
            ),
        ],
        duration_ms=2,
    )
    assert result.retrieved_sources == [source]
    await repository.save_result(result)
    result.warnings.append("changed")
    assert repository.results[0].warnings == []
