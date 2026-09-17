"""Provider failure classification and cooldown regression checks."""

from types import SimpleNamespace

import httpx
import pytest
from ai.providers.base import ProviderError

from researcher.services.retry_policy import ProviderWait, retry_external_error


@pytest.mark.parametrize("status,expected", [(400, False), (401, False), (429, True), (503, True)])
def test_http_retry_classification(status: int, expected: bool) -> None:
    response = httpx.Response(status, request=httpx.Request("GET", "https://example.test"))
    error = httpx.HTTPStatusError("failed", request=response.request, response=response)
    assert retry_external_error(error) is expected


def test_wrapped_provider_bad_request_is_not_retried() -> None:
    cause = RuntimeError("invalid request")
    cause.code = 400
    error = ProviderError("provider failed")
    error.__cause__ = cause
    assert not retry_external_error(error)


def test_gemini_cooldown_overrides_short_backoff() -> None:
    error = ProviderError("429: Please retry in 56.9s.")
    state = SimpleNamespace(attempt_number=1, outcome=SimpleNamespace(exception=lambda: error))
    assert ProviderWait(multiplier=0.25, max=4)(state) == 56.9


def test_http_retry_after_is_respected() -> None:
    response = httpx.Response(
        429, headers={"Retry-After": "30"}, request=httpx.Request("GET", "https://example.test")
    )
    error = httpx.HTTPStatusError("limit", request=response.request, response=response)
    state = SimpleNamespace(attempt_number=1, outcome=SimpleNamespace(exception=lambda: error))
    assert ProviderWait(multiplier=0.25, max=4)(state) == 30
