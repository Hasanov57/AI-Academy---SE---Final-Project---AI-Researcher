"""Regression tests for complete Gemini answers through the supplied interface."""

from unittest.mock import Mock

import pytest
from ai.providers.base import ProviderError

from researcher.services.llm_adapter import ResearchLLM


def test_adapter_reserves_room_for_reasoning_and_preserves_answer() -> None:
    provider = Mock()
    provider.complete.return_value = "Evidence [1]."
    assert ResearchLLM(provider).complete("question") == "Evidence [1]."
    assert provider.complete.call_args.kwargs["max_tokens"] == 8192


def test_adapter_preserves_larger_requested_budget_and_schema() -> None:
    provider = Mock()
    provider.complete.return_value = "{}"
    schema = {"type": "object"}
    ResearchLLM(provider).complete("question", json_schema=schema, max_tokens=10000)
    provider.complete.assert_called_once_with("question", json_schema=schema, max_tokens=10000)


def test_adapter_preserves_provider_error_for_retry_policy() -> None:
    provider = Mock()
    provider.complete.side_effect = ProviderError("unavailable")
    with pytest.raises(ProviderError, match="unavailable"):
        ResearchLLM(provider).complete("question")
