"""Resilient wrapper around the provided synchronous ``ai.synthesize`` call."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Callable

from ai import AnswerWithCitations, Source, synthesize
from ai.providers.base import LLMProvider
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt

from researcher.config import Settings
from researcher.errors import CitationValidationError
from researcher.services.retry_policy import ProviderWait, retry_external_error

Synthesizer = Callable[..., AnswerWithCitations]
_CITATION_MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


class SynthesisService:
    """Run synthesis off the event loop and validate its citation contract."""

    def __init__(
        self,
        settings: Settings,
        *,
        llm: LLMProvider | None = None,
        synthesizer: Synthesizer = synthesize,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._synthesizer = synthesizer
        self._logger = logging.getLogger(__name__)

    async def synthesize(self, question: str, sources: list[Source]) -> AnswerWithCitations:
        """Synthesize with timeout/retries and reject dangling citation indices."""
        started = time.perf_counter()
        policy_question = _add_evidence_policy(question)
        attempt_question = policy_question
        retryer = AsyncRetrying(
            stop=stop_after_attempt(self._settings.max_retry_attempts),
            wait=ProviderWait(
                multiplier=max(self._settings.retry_min_wait_seconds, 0.001),
                min=self._settings.retry_min_wait_seconds,
                max=self._settings.retry_max_wait_seconds,
            ),
            retry=retry_if_exception(
                lambda error: isinstance(error, CitationValidationError)
                or retry_external_error(error)
            ),
            reraise=True,
        )

        async for attempt in retryer:
            with attempt:
                async with asyncio.timeout(self._settings.synthesis_timeout_seconds):
                    answer = await asyncio.to_thread(
                        self._synthesizer,
                        attempt_question,
                        sources,
                        llm=self._llm,
                    )
                answer = answer.model_copy(update={"question": question})
                self._logger.debug("synthesis_attempt_payload payload=%r", answer)
                try:
                    validate_citations(answer, sources)
                except CitationValidationError as exc:
                    self._logger.warning("synthesis_validation_failed error=%s", exc)
                    attempt_question = _add_retry_feedback(policy_question, str(exc))
                    raise

        duration_ms = (time.perf_counter() - started) * 1000
        self._logger.info(
            "synthesis_finished citations=%d duration_ms=%.2f",
            len(answer.citations),
            duration_ms,
        )
        self._logger.debug("synthesis_payload payload=%r", answer)
        return answer


def _add_evidence_policy(question: str) -> str:
    """Tell the supplied synthesizer how to balance the available evidence."""
    return (
        f"{question}\n\n"
        "Evidence policy: write exactly 3 concise, complete sentences with inline [N] citations. "
        "First use relevant Wikipedia or arXiv evidence. If those sources do not adequately answer "
        "the question, use relevant credible web evidence. Never cite an irrelevant source merely "
        "to increase citation count."
    )


def _add_retry_feedback(policy_question: str, error: str) -> str:
    """Tell the next LLM attempt exactly how the previous response was invalid."""
    return (
        f"{policy_question}\n\n"
        f"Correction required: the previous response failed validation because: {error}. "
        "Return only the corrected answer. It must have exactly 3 short, complete sentences, "
        "end with punctuation, and include a valid [N] citation after every factual claim."
    )


def validate_citations(answer: AnswerWithCitations, sources: list[Source]) -> None:
    """Require a complete, grounded answer whose markers match indexed sources."""
    source_count = len(sources)
    markers: set[int] = set()
    for match in _CITATION_MARKER.finditer(answer.answer):
        markers.update(int(part.strip()) for part in match.group(1).split(","))
    if not markers:
        raise CitationValidationError("The synthesized answer contains no citation markers")
    invalid = sorted(index for index in markers if not 1 <= index <= source_count)
    if invalid:
        raise CitationValidationError(f"Invalid citation indices: {invalid}")
    declared = {citation.index for citation in answer.citations}
    if declared != markers:
        raise CitationValidationError("Citation list does not match answer markers")
    if len(declared) != len(answer.citations):
        raise CitationValidationError("Citation indices must not be duplicated")
    for citation in answer.citations:
        if citation.source != sources[citation.index - 1]:
            raise CitationValidationError("Citation source does not match its marker index")
    answer_text = answer.answer.strip()
    if not answer_text.endswith((".", "!", "?")):
        raise CitationValidationError("The synthesized answer ends with an incomplete sentence")
    sentences = [sentence for sentence in _SENTENCE.split(answer_text) if sentence.strip()]
    if not 3 <= len(sentences) <= 6:
        raise CitationValidationError("The synthesized answer must contain 3-6 sentences")
