"""Pure text renderers shared by the CLI and scripted demo."""

from __future__ import annotations

from researcher.models import ResearchResult


def render_text(result: ResearchResult) -> str:
    """Render a readable terminal answer with timings and references."""
    lines = [
        f"Question: {result.question}",
        "",
        result.answer.answer,
        "",
        "References:",
    ]
    for citation in result.answer.citations:
        lines.extend(
            [
                f"  [{citation.index}] ({citation.source.origin}) {citation.source.title}",
                f"      {citation.source.url}",
            ]
        )
    if result.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"  - {warning}" for warning in result.warnings)
    source_timing = ", ".join(
        f"{fetch.source.value}={fetch.duration_ms:.0f}ms" + (" cache" if fetch.cache_hit else "")
        for fetch in result.fetches
    )
    lines.extend(
        [
            "",
            f"Session: {result.session_id}",
            f"Timing: total={result.duration_ms:.0f}ms; {source_timing}",
        ]
    )
    return "\n".join(lines)


def render_markdown(result: ResearchResult) -> str:
    """Render a result as a portable Markdown artefact."""
    lines = [
        f"# Research answer: {result.question}",
        "",
        result.answer.answer,
        "",
        "## References",
        "",
    ]
    lines.extend(
        f"{citation.index}. [{citation.source.title}]({citation.source.url}) "
        f"- {citation.source.origin}"
        for citation in result.answer.citations
    )
    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result.warnings)
    lines.extend(["", f"Generated in {result.duration_ms:.0f} ms.", ""])
    return "\n".join(lines)
