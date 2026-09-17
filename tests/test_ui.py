"""Tests for the thin Streamlit adapter."""

from researcher.models import SourceName
from researcher.ui import selected_sources


def test_selected_sources_preserves_display_order() -> None:
    assert selected_sources(wiki=True, arxiv=True, web=True) == (
        SourceName.WIKIPEDIA,
        SourceName.ARXIV,
        SourceName.WEB,
    )


def test_selected_sources_allows_a_subset() -> None:
    assert selected_sources(wiki=False, arxiv=True, web=False) == (SourceName.ARXIV,)
