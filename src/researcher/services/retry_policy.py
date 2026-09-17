"""Retry transient failures and respect provider cooldowns."""

import re

import httpx
from ai.providers.base import ProviderError
from tenacity import RetryCallState, wait_exponential


def retry_external_error(error: BaseException) -> bool:
    """Do not spend requests retrying invalid credentials or bad requests."""
    if "GenerateRequestsPerDay" in str(error):
        return False
    cause = error.__cause__ or error
    status = getattr(cause, "code", None)
    if isinstance(cause, httpx.HTTPStatusError):
        status = cause.response.status_code
    if isinstance(status, int) and 400 <= status < 500:
        return status in (408, 429)
    return isinstance(error, (ProviderError, httpx.HTTPError, TimeoutError))


class ProviderWait(wait_exponential):
    """Use exponential backoff, or a longer API-specified retry delay."""

    def __call__(self, retry_state: RetryCallState) -> float:
        delay = float(super().__call__(retry_state))
        error = retry_state.outcome.exception() if retry_state.outcome else None
        if error is None:
            return delay
        cause = error.__cause__ or error
        if isinstance(cause, httpx.HTTPStatusError):
            header = cause.response.headers.get("Retry-After", "")
            if header.isdigit():
                delay = max(delay, float(header))
        match = re.search(
            r"retry(?: in|Delay['\"]?:\s*['\"]?)\s*(\d+(?:\.\d+)?)s", str(error), re.I
        )
        if match:
            delay = max(delay, float(match.group(1)))
        return delay
