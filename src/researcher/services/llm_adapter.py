"""Configure the supplied LLM through its public interface."""

from typing import Any, cast

from ai.providers.base import LLMProvider


class ResearchLLM:
    """Leave room for Gemini reasoning as well as the short visible answer."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def complete(
        self,
        prompt: str,
        *,
        json_schema: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> str:
        return cast(
            str,
            self.provider.complete(
                prompt, json_schema=json_schema, max_tokens=max(max_tokens, 8192)
            ),
        )
