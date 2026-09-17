"""Query selected sources concurrently while isolating failures."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from researcher.config import Settings
from researcher.models import SourceFetchOutcome, SourceName
from researcher.services.source_service import SourceService


class SourceOrchestrator:
    """Coordinate source I/O with bounded parallelism and graceful degradation."""

    def __init__(self, settings: Settings, source_service: SourceService) -> None:
        self._settings = settings
        self._source_service = source_service
        self._semaphore = asyncio.Semaphore(settings.max_parallel_sources)
        self._logger = logging.getLogger(__name__)

    async def fetch_all(
        self,
        question: str,
        sources: tuple[SourceName, ...],
        *,
        no_cache: bool,
        concurrent: bool = True,
    ) -> list[SourceFetchOutcome]:
        """Fetch all requested sources concurrently or as a benchmark baseline."""
        timeout = httpx.Timeout(self._settings.per_source_timeout_seconds)
        limits = httpx.Limits(max_connections=self._settings.max_parallel_sources + 2)
        headers = {
            "User-Agent": self._settings.http_user_agent,
            "Api-User-Agent": self._settings.http_user_agent,
            "Accept": "application/json, application/atom+xml;q=0.9, */*;q=0.8",
        }
        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            headers=headers,
            follow_redirects=True,
        ) as client:
            if not concurrent:
                outcomes = []
                for source in sources:
                    outcomes.append(
                        await self._safe_fetch(source, question, no_cache=no_cache, client=client)
                    )
                return outcomes
            tasks = [
                asyncio.create_task(
                    self._bounded_fetch(source, question, no_cache=no_cache, client=client),
                    name=f"fetch-{source.value}",
                )
                for source in sources
            ]
            return list(await asyncio.gather(*tasks))

    async def _bounded_fetch(
        self,
        source: SourceName,
        question: str,
        *,
        no_cache: bool,
        client: httpx.AsyncClient,
    ) -> SourceFetchOutcome:
        async with self._semaphore:
            return await self._safe_fetch(source, question, no_cache=no_cache, client=client)

    async def _safe_fetch(
        self,
        source: SourceName,
        question: str,
        *,
        no_cache: bool,
        client: httpx.AsyncClient,
    ) -> SourceFetchOutcome:
        started = time.perf_counter()
        try:
            return await self._source_service.fetch(
                source,
                question,
                no_cache=no_cache,
                client=client,
            )
        except (RuntimeError, httpx.HTTPError, TimeoutError) as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            self._logger.warning(
                "source_fetch_failed source=%s error=%s duration_ms=%.2f",
                source.value,
                exc,
                duration_ms,
            )
            return SourceFetchOutcome(
                source=source,
                duration_ms=duration_ms,
                error=str(exc),
            )
