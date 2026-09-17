"""End-to-end research use case independent of CLI and storage implementation."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from researcher.concurrency.orchestrator import SourceOrchestrator
from researcher.errors import NoSourcesError, StorageError
from researcher.models import ResearchRequest, ResearchResult
from researcher.services.synthesis_service import SynthesisService
from researcher.storage.base import ResearchRepository
from researcher.utils import deduplicate_sources


class Researcher:
    """Compose source orchestration, synthesis and persistence into one use case."""

    def __init__(
        self,
        orchestrator: SourceOrchestrator,
        synthesis: SynthesisService,
        repository: ResearchRepository,
    ) -> None:
        self._orchestrator = orchestrator
        self._synthesis = synthesis
        self._repository = repository
        self._logger = logging.getLogger(__name__)

    async def ask(self, request: ResearchRequest, *, concurrent: bool = True) -> ResearchResult:
        """Research a question and persist the cited answer with an audit trail."""
        started_clock = time.perf_counter()
        started_at = datetime.now(UTC)
        fetches = await self._orchestrator.fetch_all(
            request.question,
            request.sources,
            no_cache=request.no_cache,
            concurrent=concurrent,
        )
        warnings = [
            f"{fetch.source.value} unavailable: {fetch.error}"
            for fetch in fetches
            if fetch.error is not None
        ]
        sources = deduplicate_sources([source for fetch in fetches for source in fetch.sources])
        if not sources:
            raise NoSourcesError("No selected source returned usable information")

        answer = await self._synthesis.synthesize(request.question, sources)
        result = ResearchResult(
            question=request.question,
            requested_sources=request.sources,
            answer=answer,
            fetches=fetches,
            warnings=warnings,
            started_at=started_at,
            duration_ms=(time.perf_counter() - started_clock) * 1000,
        )
        try:
            await self._repository.save_result(result)
        except StorageError as exc:
            self._logger.error("result_persistence_failed error=%s", exc)
            result.warnings.append(f"result was not persisted: {exc}")
        self._logger.info(
            "research_completed session_id=%s sources=%d duration_ms=%.2f",
            result.session_id,
            len(sources),
            result.duration_ms,
        )
        return result
