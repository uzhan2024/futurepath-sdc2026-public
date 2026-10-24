"""Typed, vendor-neutral request and response contracts for language models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMCompletionRequest:
    feature: str
    system_prompt: str
    user_prompt: str
    max_output_tokens: int
    reasoning_effort: str = "low"
    response_schema: dict | None = None


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None = None


@dataclass(frozen=True)
class LLMCompletionResponse:
    content: str
    usage: LLMUsage | None
    model: str
    latency_ms: float | None = None


class LLMProvider(Protocol):
    """A provider accepts bounded text and returns untrusted generated text."""

    def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        """Return one non-streamed completion or raise a sanitized provider error."""


class ProviderConfigurationError(RuntimeError):
    """The server-side provider configuration is incomplete."""


class ProviderFailure(RuntimeError):
    """A provider request failed without exposing the SDK's raw error body."""

    def __init__(self, category: str, status_code: int | None = None):
        super().__init__(category)
        self.category = category
        self.status_code = status_code
