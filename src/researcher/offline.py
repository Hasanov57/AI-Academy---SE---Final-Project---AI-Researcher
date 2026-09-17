"""Deterministic providers for demonstrations and network-free verification."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import Any

from ai import Source

from researcher.models import SourceName

OfflineFetcher = Callable[..., Awaitable[list[Source]]]


class OfflineLLM:
    """Produce a deterministic answer with a citation on every sentence."""

    def complete(
        self,
        prompt: str,
        *,
        json_schema: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Return stable prose derived from the number of indexed sources."""
        del json_schema, max_tokens
        source_count = len(re.findall(r"^\[(\d+)\]", prompt, re.MULTILINE))
        if source_count == 0:
            return "The available material is insufficient to answer safely."
        first = "[1]"
        group = "[1]" if source_count == 1 else f"[1,{min(source_count, 2)}]"
        return (
            f"The collected references provide a grounded overview of the question {first}. "
            "Their combined evidence supports the main explanation while preserving "
            f"source attribution {group}. "
            f"The result remains traceable to the indexed evidence {first}."
        )


def build_offline_fetchers(delay_seconds: float = 0.08) -> dict[SourceName, OfflineFetcher]:
    """Return one latency-simulating fetcher for each source selector."""

    async def wikipedia(question: str, **_: Any) -> list[Source]:
        await asyncio.sleep(delay_seconds)
        return [
            Source(
                title=f"Wikipedia overview: {question[:60]}",
                url="https://en.wikipedia.org/wiki/Research",
                snippet=f"An encyclopedia overview relevant to {question}",
                origin="wikipedia",
            )
        ]

    async def arxiv(question: str, **_: Any) -> list[Source]:
        await asyncio.sleep(delay_seconds)
        return [
            Source(
                title=f"Research paper: {question[:60]}",
                url="https://arxiv.org/abs/2401.00001",
                snippet=f"A representative academic abstract relevant to {question}",
                origin="arxiv",
            )
        ]

    async def web(question: str, **_: Any) -> list[Source]:
        await asyncio.sleep(delay_seconds)
        return [
            Source(
                title=f"Web reference: {question[:60]}",
                url="https://example.com/research-reference",
                snippet=f"A representative web excerpt relevant to {question}",
                origin="web",
            )
        ]

    return {
        SourceName.WIKIPEDIA: wikipedia,
        SourceName.ARXIV: arxiv,
        SourceName.WEB: web,
    }
