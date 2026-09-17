"""Composition root: create concrete adapters and wire application services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from ai import DuckDuckGoProvider, SerperProvider, Source, TavilyProvider, fetch_web
from ai.providers.anthropic import AnthropicLLM
from ai.providers.base import LLMProvider
from ai.providers.google import GeminiLLM
from ai.providers.openai import OpenAILLM
from ai.sources import WebSearchProvider

from researcher.concurrency.orchestrator import SourceOrchestrator
from researcher.config import Settings
from researcher.core.researcher import Researcher
from researcher.models import SourceName
from researcher.offline import OfflineLLM, build_offline_fetchers
from researcher.services.llm_adapter import ResearchLLM
from researcher.services.source_service import SourceFetcher, SourceService
from researcher.services.synthesis_service import SynthesisService
from researcher.storage.base import ResearchRepository
from researcher.storage.memory import MemoryRepository
from researcher.storage.postgres import PostgresRepository


@dataclass(slots=True)
class ApplicationRuntime:
    """Resources created together and closed together at the process boundary."""

    researcher: Researcher
    orchestrator: SourceOrchestrator
    repository: ResearchRepository

    async def close(self) -> None:
        """Release storage connections."""
        await self.repository.close()


async def build_runtime(settings: Settings, *, offline: bool = False) -> ApplicationRuntime:
    """Build and initialize a complete application object graph."""
    repository = _build_repository(settings, offline=offline)
    await repository.initialize()

    if offline:
        source_service = SourceService(
            settings,
            repository,
            fetchers=build_offline_fetchers(),
        )
        llm: LLMProvider = OfflineLLM()
    else:
        settings.validate_live_credentials()
        source_service = SourceService(
            settings,
            repository,
            fetchers=_build_live_fetchers(settings),
        )
        llm = _build_llm(settings)

    orchestrator = SourceOrchestrator(settings, source_service)
    synthesis = SynthesisService(settings, llm=llm)
    researcher = Researcher(orchestrator, synthesis, repository)
    return ApplicationRuntime(researcher, orchestrator, repository)


def _build_repository(settings: Settings, *, offline: bool) -> ResearchRepository:
    if offline or settings.storage_backend == "memory":
        return MemoryRepository()
    return PostgresRepository(settings.database_url.get_secret_value())


def _build_llm(settings: Settings) -> LLMProvider:
    key_by_provider = {
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
        "gemini": settings.google_api_key,
    }
    secret = key_by_provider[settings.llm_provider]
    api_key = secret.get_secret_value() if secret is not None else None
    if settings.llm_provider == "openai":
        return OpenAILLM(model=settings.llm_model, api_key=api_key)
    if settings.llm_provider == "anthropic":
        return AnthropicLLM(model=settings.llm_model, api_key=api_key)
    return ResearchLLM(GeminiLLM(model=settings.llm_model, api_key=api_key))


def _build_live_fetchers(settings: Settings) -> dict[SourceName, SourceFetcher]:
    from ai import fetch_arxiv, fetch_wikipedia

    provider = _build_web_provider(settings)

    async def configured_web_fetcher(
        query: str,
        *,
        max_results: int = 3,
        client: Any = None,
        **_: Any,
    ) -> list[Source]:
        return cast(
            list[Source],
            await fetch_web(
                query,
                max_results=max_results,
                provider=provider,
                client=client,
            ),
        )

    return {
        SourceName.WIKIPEDIA: fetch_wikipedia,
        SourceName.ARXIV: fetch_arxiv,
        SourceName.WEB: configured_web_fetcher,
    }


def _build_web_provider(settings: Settings) -> WebSearchProvider:
    if settings.web_search_provider == "tavily":
        key = settings.tavily_api_key
        return TavilyProvider(api_key=key.get_secret_value() if key else None)
    if settings.web_search_provider == "serper":
        key = settings.serper_api_key
        return SerperProvider(api_key=key.get_secret_value() if key else None)
    return DuckDuckGoProvider()
