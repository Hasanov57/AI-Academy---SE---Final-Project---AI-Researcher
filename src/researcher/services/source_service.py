"""Retrying, cached and observable wrappers around ``ai.fetch_*``."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from ai import Source, fetch_arxiv, fetch_web, fetch_wikipedia
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt

from researcher.config import Settings
from researcher.models import SourceFetchOutcome, SourceName
from researcher.services.rate_limiter import AsyncRateLimiter
from researcher.services.retry_policy import ProviderWait, retry_external_error
from researcher.storage.base import ResearchRepository
from researcher.utils import (
    canonicalize_query,
    fallback_research_queries,
    prefer_text_web_sources,
    simplify_research_query,
)

SourceFetcher = Callable[..., Awaitable[list[Source]]]


class SourceService:
    """Add caching, retries, timeouts, rate limits and logging to source fetchers."""

    def __init__(
        self,
        settings: Settings,
        repository: ResearchRepository,
        *,
        fetchers: dict[SourceName, SourceFetcher] | None = None,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._fetchers = fetchers or {
            SourceName.WIKIPEDIA: fetch_wikipedia,
            SourceName.ARXIV: fetch_arxiv,
            SourceName.WEB: fetch_web,
        }
        self._limiters = {
            SourceName.WIKIPEDIA: AsyncRateLimiter(0),
            SourceName.ARXIV: AsyncRateLimiter(settings.arxiv_min_interval_seconds),
            SourceName.WEB: AsyncRateLimiter(0),
        }
        self._logger = logging.getLogger(__name__)

    async def fetch(
        self,
        source: SourceName,
        question: str,
        *,
        no_cache: bool,
        client: httpx.AsyncClient,
    ) -> SourceFetchOutcome:
        """Fetch one origin with a TTL cache and a bounded retry policy."""
        started = time.perf_counter()
        query_key = canonicalize_query(question)
        if not no_cache:
            cached = await self._repository.get_cached_sources(source, query_key)
            if cached is not None:
                duration_ms = (time.perf_counter() - started) * 1000
                self._logger.info(
                    "source_cache_hit source=%s count=%d duration_ms=%.2f",
                    source.value,
                    len(cached),
                    duration_ms,
                )
                return SourceFetchOutcome(
                    source=source,
                    sources=cached,
                    cache_hit=True,
                    duration_ms=duration_ms,
                )

        fetcher = self._fetchers[source]
        provider_query = (
            question if source is SourceName.WEB else simplify_research_query(question)
        )
        retryer = AsyncRetrying(
            stop=stop_after_attempt(self._settings.max_retry_attempts),
            wait=ProviderWait(
                multiplier=max(self._settings.retry_min_wait_seconds, 0.001),
                min=self._settings.retry_min_wait_seconds,
                max=self._settings.retry_max_wait_seconds,
            ),
            retry=retry_if_exception(retry_external_error),
            reraise=True,
        )

        self._logger.info("source_fetch_started source=%s", source.value)
        async for attempt in retryer:
            with attempt:
                await self._limiters[source].acquire()
                async with asyncio.timeout(self._settings.per_source_timeout_seconds):
                    kwargs: dict[str, Any] = {
                        "max_results": self._settings.max_sources_per_query,
                        "client": client,
                    }
                    fetched = await fetcher(provider_query, **kwargs)
                    if source is SourceName.WIKIPEDIA and not fetched:
                        for fallback_query in fallback_research_queries(provider_query):
                            self._logger.info("wikipedia_query_relaxed query=%s", fallback_query)
                            fetched = await fetcher(fallback_query, **kwargs)
                            if fetched:
                                break
        if source is SourceName.WEB:
            fetched = prefer_text_web_sources(fetched)

        if not no_cache:
            await self._repository.put_cached_sources(
                source,
                query_key,
                fetched,
                self._settings.cache_ttl_seconds,
            )
        duration_ms = (time.perf_counter() - started) * 1000
        self._logger.info(
            "source_fetch_finished source=%s count=%d duration_ms=%.2f",
            source.value,
            len(fetched),
            duration_ms,
        )
        self._logger.debug("source_fetch_payload source=%s payload=%r", source.value, fetched)
        return SourceFetchOutcome(
            source=source,
            sources=fetched,
            cache_hit=False,
            duration_ms=duration_ms,
        )
