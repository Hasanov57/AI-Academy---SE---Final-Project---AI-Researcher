"""Tests for clean user-facing parsing and rendering."""

from __future__ import annotations

import argparse

import pytest
from ai import AnswerWithCitations, Citation, Source

from researcher.cli import parse_sources
from researcher.models import ResearchResult, SourceFetchOutcome, SourceName
from researcher.rendering import render_markdown, render_text


def make_result() -> ResearchResult:
    source = Source(title="Reference", url="https://example.com", snippet="s", origin="web")
    return ResearchResult(
        question="Question?",
        requested_sources=(SourceName.WEB,),
        answer=AnswerWithCitations(
            question="Question?",
            answer="A grounded answer appears here [1].",
            citations=[Citation(index=1, source=source)],
        ),
        fetches=[
            SourceFetchOutcome(
                source=SourceName.WEB, sources=[source], cache_hit=True, duration_ms=2
            )
        ],
        warnings=["wiki unavailable"],
        duration_ms=5,
    )


def test_parse_sources_supports_aliases_and_dedupes() -> None:
    assert parse_sources("wikipedia,web,web") == (
        SourceName.WIKIPEDIA,
        SourceName.WEB,
    )


def test_parse_sources_rejects_unknown_value() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_sources("reddit")


def test_text_renderer_contains_references_warnings_and_timing() -> None:
    output = render_text(make_result())
    assert "References:" in output
    assert "wiki unavailable" in output
    assert "web=2ms cache" in output


def test_markdown_renderer_contains_clickable_source() -> None:
    output = render_markdown(make_result())
    assert "[Reference](https://example.com)" in output
    assert "## Warnings" in output
