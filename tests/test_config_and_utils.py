"""Unit tests for validation and pure canonicalization helpers."""

from __future__ import annotations

import pytest
from ai import Source
from pydantic import ValidationError

from researcher.config import Settings
from researcher.models import ResearchRequest, SourceName
from researcher.utils import (
    canonicalize_query,
    canonicalize_url,
    deduplicate_sources,
    fallback_research_queries,
    prefer_text_web_sources,
    simplify_research_query,
)


def test_settings_rejects_reversed_retry_window() -> None:
    with pytest.raises(ValidationError):
        Settings(retry_min_wait_seconds=5, retry_max_wait_seconds=1)


def test_live_credentials_reports_missing_llm_key() -> None:
    settings = Settings(
        llm_provider="openai",
        openai_api_key=None,
        tavily_api_key="web-key",
    )
    with pytest.raises(ValueError, match="Missing API key"):
        settings.validate_live_credentials()


def test_live_credentials_accepts_required_keys() -> None:
    settings = Settings(
        google_api_key="llm-key",
        tavily_api_key="web-key",
        http_user_agent="CourseResearcher/1.0 (contact: student@university.edu)",
    )
    settings.validate_live_credentials()


def test_research_request_normalizes_and_deduplicates() -> None:
    request = ResearchRequest(
        question="  What   is AI?  ",
        sources=(SourceName.WEB, SourceName.WEB, SourceName.ARXIV),
    )
    assert request.question == "What is AI?"
    assert request.sources == (SourceName.WEB, SourceName.ARXIV)


def test_research_request_rejects_empty_source_selection() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(question="valid", sources=())


def test_canonicalize_query_is_case_and_whitespace_insensitive() -> None:
    assert canonicalize_query("  WHAT   Is Photosynthesis? ") == "what is photosynthesis?"
    assert (
        simplify_research_query(
            "What are the latest developments in nuclear fusion energy?"
        )
        == "nuclear fusion energy"
    )
    assert fallback_research_queries("nuclear fusion energy") == (
        "nuclear fusion",
        "nuclear",
    )


def test_canonicalize_url_removes_tracking_and_fragment() -> None:
    url = "HTTPS://Example.COM/a//b/?utm_source=x&keep=yes#section"
    assert canonicalize_url(url) == "https://example.com/a/b?keep=yes"


def test_deduplicate_sources_preserves_first_occurrence() -> None:
    first = Source(
        title="First",
        url="https://example.com/a?utm_source=x",
        snippet="x",
        origin="web",
    )
    duplicate = Source(title="Second", url="https://example.com/a", snippet="y", origin="web")
    assert deduplicate_sources([first, duplicate]) == [first]
    youtube = Source(
        title="Video",
        url="https://www.youtube.com/watch?v=123",
        snippet="video",
        origin="web",
    )
    second_text = Source(
        title="Second text source",
        url="https://example.org/report",
        snippet="report",
        origin="web",
    )
    assert prefer_text_web_sources([first, youtube, second_text]) == [first, second_text]
