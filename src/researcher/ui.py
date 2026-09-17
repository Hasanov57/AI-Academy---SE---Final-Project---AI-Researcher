"""Small Streamlit interface over the existing research use case."""

from __future__ import annotations

import asyncio

import streamlit as st
from ai.providers.base import ProviderError
from pydantic import ValidationError

from researcher.bootstrap import build_runtime
from researcher.config import Settings
from researcher.errors import ResearcherError
from researcher.logging_config import configure_logging
from researcher.models import ResearchRequest, ResearchResult, SourceName


def selected_sources(*, wiki: bool, arxiv: bool, web: bool) -> tuple[SourceName, ...]:
    """Convert checkbox state into the typed source selectors used by the core layer."""
    selections = []
    if wiki:
        selections.append(SourceName.WIKIPEDIA)
    if arxiv:
        selections.append(SourceName.ARXIV)
    if web:
        selections.append(SourceName.WEB)
    return tuple(selections)


async def research(settings: Settings, request: ResearchRequest) -> ResearchResult:
    """Create, use and close one runtime inside a single event loop."""
    runtime = await build_runtime(settings)
    try:
        return await runtime.researcher.ask(request)
    finally:
        await runtime.close()


def run_research(settings: Settings, request: ResearchRequest) -> ResearchResult:
    """Run the asynchronous application safely for one Streamlit form submission."""
    return asyncio.run(research(settings, request))


def _render_result(result: ResearchResult) -> None:
    st.subheader("Answer")
    st.markdown(result.answer.answer)

    st.subheader("References")
    for citation in result.answer.citations:
        with st.container(border=True):
            st.markdown(
                f"**[{citation.index}] {citation.source.title}**  \n"
                f"Source type: `{citation.source.origin}`"
            )
            st.link_button("Open source", citation.source.url)

    if result.warnings:
        st.subheader("Warnings")
        for warning in result.warnings:
            st.warning(warning)

    st.subheader("Timing")
    columns = st.columns(len(result.fetches) + 1)
    columns[0].metric("Total", f"{result.duration_ms / 1000:.2f} s")
    for column, fetch in zip(columns[1:], result.fetches, strict=True):
        suffix = " (cache)" if fetch.cache_hit else ""
        column.metric(fetch.source.value.title(), f"{fetch.duration_ms:.0f} ms{suffix}")
    st.caption(f"Session: {result.session_id}")


def main() -> None:
    """Render the Streamlit page without duplicating business logic."""
    st.set_page_config(
        page_title="Async Research Assistant",
        page_icon="🔎",
        layout="wide",
    )
    st.title("Async Research Assistant")
    st.write(
        "Ask one research question. The assistant searches selected sources in parallel "
        "and returns a concise answer with citations."
    )

    with st.sidebar:
        st.header("Research settings")
        use_wiki = st.checkbox("Wikipedia", value=True)
        use_arxiv = st.checkbox("arXiv", value=True)
        use_web = st.checkbox("Web search", value=True)
        fresh_results = st.checkbox("Bypass cache", value=False)

    with st.form("research-form"):
        question = st.text_area(
            "Research question",
            placeholder="What are the latest developments in nuclear fusion energy?",
            height=120,
            max_chars=1000,
        )
        submitted = st.form_submit_button("Research", type="primary", use_container_width=True)

    if not submitted:
        return

    sources = selected_sources(wiki=use_wiki, arxiv=use_arxiv, web=use_web)
    if not sources:
        st.error("Select at least one research source.")
        return

    try:
        settings = Settings()
        configure_logging(settings.log_level)
        request = ResearchRequest(
            question=question,
            sources=sources,
            no_cache=fresh_results,
        )
        with st.spinner("Searching sources and preparing a cited answer..."):
            result = run_research(settings, request)
    except (ResearcherError, ProviderError, ValidationError, ValueError) as exc:
        st.error(str(exc))
        return

    _render_result(result)


if __name__ == "__main__":
    main()
