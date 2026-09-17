"""Citation validation and synthesis retry tests."""

from __future__ import annotations

from typing import Any

import pytest
from ai import AnswerWithCitations, Citation, Source

from researcher.config import Settings
from researcher.errors import CitationValidationError
from researcher.services.synthesis_service import SynthesisService, validate_citations

SOURCE = Source(title="Evidence", url="https://example.com", snippet="text", origin="web")
def answer(text: str, indices: list[int]) -> AnswerWithCitations:
    return AnswerWithCitations(
        question="Q",
        answer=text,
        citations=[Citation(index=index, source=SOURCE) for index in indices],
    )


def test_validate_citations_accepts_grounded_sentences() -> None:
    value = (
        "A sufficiently detailed claim is supported here [1]. "
        "The evidence provides useful explanatory context [1]. "
        "The conclusion remains traceable to that source [1]."
    )
    validate_citations(answer(value, [1]), [SOURCE])


def test_validate_citations_does_not_require_a_marker_in_every_sentence() -> None:
    value = (
        "A sufficiently detailed claim is supported by evidence [1]. "
        "This short transition explains why the conclusion follows. "
        "The final evidence-based conclusion remains traceable [1]."
    )
    validate_citations(answer(value, [1]), [SOURCE])


@pytest.mark.parametrize(
    ("value", "indices", "message"),
    [
        ("There is no marker in this substantive sentence.", [], "no citation"),
        ("This sentence cites an invalid source number [2].", [], "Invalid citation"),
        ("This sentence names a source marker [1].", [], "does not match"),
    ],
)
def test_validate_citations_rejects_invalid_answers(
    value: str, indices: list[int], message: str
) -> None:
    with pytest.raises(CitationValidationError, match=message):
        validate_citations(answer(value, indices), [SOURCE])


def test_validate_citations_rejects_incomplete_answer() -> None:
    value = (
        "The first complete claim cites its supporting evidence [1]. "
        "The second complete claim also cites the evidence [1]. In"
    )
    with pytest.raises(CitationValidationError, match="incomplete"):
        validate_citations(answer(value, [1]), [SOURCE])


async def test_synthesis_retries_invalid_citation_output() -> None:
    calls = 0
    questions: list[str] = []

    def fake(question: str, sources: list[Source], **_: Any) -> AnswerWithCitations:
        nonlocal calls
        calls += 1
        questions.append(question)
        if calls == 1:
            return answer("This first response forgot its citation marker.", [])
        return answer(
            "This corrected response includes trustworthy evidence [1]. "
            "A second complete sentence remains grounded in that evidence [1]. "
            "The concise conclusion also preserves its attribution [1].",
            [1],
        )

    settings = Settings(
        storage_backend="memory",
        max_retry_attempts=2,
        retry_min_wait_seconds=0,
        retry_max_wait_seconds=0,
    )
    result = await SynthesisService(settings, synthesizer=fake).synthesize("Q", [SOURCE])
    assert calls == 2
    assert result.citations[0].index == 1
    assert result.question == "Q"
    assert "previous response failed validation" in questions[1]
    assert "contains no citation markers" in questions[1]
