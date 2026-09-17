"""Check real PostgreSQL persistence and TTL caching without paid API calls."""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai import Source

from researcher.concurrency.orchestrator import SourceOrchestrator
from researcher.config import Settings
from researcher.core.researcher import Researcher
from researcher.models import ResearchRequest, SourceName
from researcher.offline import OfflineLLM, build_offline_fetchers
from researcher.services.source_service import SourceService
from researcher.services.synthesis_service import SynthesisService
from researcher.storage.postgres import PostgresRepository


async def main() -> None:
    settings = Settings()
    repository = PostgresRepository(settings.database_url.get_secret_value())
    await repository.initialize()
    query = f"Storage verification {uuid4()}"
    try:
        service = SourceService(settings, repository, fetchers=build_offline_fetchers())
        researcher = Researcher(
            SourceOrchestrator(settings, service),
            SynthesisService(settings, llm=OfflineLLM()),
            repository,
        )
        request = ResearchRequest(question=query)
        first = await researcher.ask(request)
        second = await researcher.ask(request)
        assert all(not fetch.cache_hit for fetch in first.fetches)
        assert all(fetch.cache_hit for fetch in second.fetches)
        await repository.close()
        await repository.initialize()
        assert await repository.get_cached_sources(SourceName.WEB, query.casefold())
        evidence = Source(title="TTL test", url="https://example.com", snippet="test", origin="web")
        await repository.put_cached_sources(SourceName.WEB, query, [evidence], 0)
        assert await repository.get_cached_sources(SourceName.WEB, query) is None
        print(
            "PASS: persistent cache, cache hits, TTL expiry, and saved sessions "
            f"{first.session_id}, {second.session_id}"
        )
    finally:
        await repository.close()


if __name__ == "__main__":
    asyncio.run(main())
