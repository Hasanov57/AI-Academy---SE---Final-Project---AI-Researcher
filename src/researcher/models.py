"""Pydantic models used across the software-engineering layer."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from ai import AnswerWithCitations, Source
from pydantic import BaseModel, ConfigDict, Field, field_validator

from researcher.utils import deduplicate_sources


class SourceName(StrEnum):
    """Source selectors accepted by the CLI and orchestrator."""

    WIKIPEDIA = "wiki"
    ARXIV = "arxiv"
    WEB = "web"


DEFAULT_SOURCES = (SourceName.WIKIPEDIA, SourceName.ARXIV, SourceName.WEB)


class ResearchRequest(BaseModel):
    """Validated input for one research operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    question: str = Field(min_length=1, max_length=1000)
    sources: tuple[SourceName, ...] = DEFAULT_SOURCES
    no_cache: bool = False

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        """Trim the question and collapse repeated whitespace."""
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("question must not be empty")
        return normalized

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, value: tuple[SourceName, ...]) -> tuple[SourceName, ...]:
        """Require at least one source and remove duplicates without reordering."""
        if not value:
            raise ValueError("at least one source must be selected")
        return tuple(dict.fromkeys(value))


class SourceFetchOutcome(BaseModel):
    """Observable result from one source fetch, including failures and timing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: SourceName
    sources: list[Source] = Field(default_factory=list)
    cache_hit: bool = False
    duration_ms: float = Field(ge=0)
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether the fetch completed without an exception."""
        return self.error is None


class ResearchResult(BaseModel):
    """Complete response returned by the core service and persisted to PostgreSQL."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID = Field(default_factory=uuid4)
    question: str
    requested_sources: tuple[SourceName, ...]
    answer: AnswerWithCitations
    fetches: list[SourceFetchOutcome]
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: float = Field(ge=0)

    @property
    def retrieved_sources(self) -> list[Source]:
        """Flatten all successfully retrieved sources in deterministic order."""
        flattened = [source for fetch in self.fetches for source in fetch.sources]
        return deduplicate_sources(flattened)
