"""Pure transformations shared by caching, orchestration and tests."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ai import Source

_RESEARCH_QUERY_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "at",
        "be",
        "been",
        "current",
        "developments",
        "do",
        "does",
        "for",
        "how",
        "in",
        "is",
        "its",
        "latest",
        "main",
        "of",
        "on",
        "state",
        "the",
        "their",
        "to",
        "was",
        "were",
        "what",
    }
)


def canonicalize_query(question: str) -> str:
    """Create a stable, case-insensitive cache key from a user question."""
    return " ".join(question.casefold().strip().split())


def simplify_research_query(question: str) -> str:
    """Reduce a natural-language question to terms suited to catalog search APIs."""
    tokens = re.findall(r"[\w-]+", question, flags=re.UNICODE)
    useful = [token for token in tokens if token.casefold() not in _RESEARCH_QUERY_STOPWORDS]
    return " ".join(useful) or " ".join(tokens)


def fallback_research_queries(query: str) -> tuple[str, ...]:
    """Return a few progressively broader catalog queries without duplicates."""
    tokens = query.split()
    candidates = [
        " ".join(tokens[:-1]),
        " ".join(tokens[: max(1, len(tokens) // 2)]),
        tokens[0] if tokens else "",
    ]
    return tuple(dict.fromkeys(item for item in candidates if item and item != query))


def canonicalize_url(url: str) -> str:
    """Normalize a URL and remove common tracking parameters."""
    parts = urlsplit(url.strip())
    ignored = {"fbclid", "gclid"}
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in ignored
    ]
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), path, urlencode(query), "")
    )


def deduplicate_sources(sources: list[Source]) -> list[Source]:
    """Remove duplicate URLs while preserving source order."""
    seen: set[str] = set()
    unique: list[Source] = []
    for source in sources:
        key = canonicalize_url(source.url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


def prefer_text_web_sources(sources: list[Source]) -> list[Source]:
    """Drop video/social results when Tavily returned enough text-based alternatives."""
    low_evidence_hosts = {
        "facebook.com",
        "instagram.com",
        "tiktok.com",
        "x.com",
        "youtu.be",
        "youtube.com",
    }
    text_sources = [
        source
        for source in sources
        if urlsplit(source.url).netloc.casefold().removeprefix("www.")
        not in low_evidence_hosts
    ]
    return text_sources if len(text_sources) >= 2 else sources
