"""OpenAI-compatible adapter for the competition-provided RunPod GLM endpoint."""

from __future__ import annotations

import json
import logging
import os

from openai import APIConnectionError, APIStatusError, APITimeoutError, BadRequestError, OpenAI

from services.llm.provider import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    LLMProvider,
    LLMUsage,
    ProviderConfigurationError,
    ProviderFailure,
)


RUNPOD_BASE_URL = "https://api.runpod.ai/v2/b1dd8hy2hqo1nb/openai/v1"
RUNPOD_MODEL = "glm-5.3"
SUPPORTED_REASONING_EFFORTS = frozenset({"low", "medium", "high"})
MAX_INPUT_BYTES = 12_000
MAX_OUTPUT_TOKENS = 512


class _PrivateTransportLogs(logging.Filter):
    """Do not emit SDK/transport records that may contain prompts or headers."""

    _futurepath_private_transport = True

    def filter(self, record: logging.LogRecord) -> bool:
        return False


def _suppress_payload_logging() -> None:
    # Parent logger filters do not apply to descendant records. Protect each
    # registered transport logger and the pinned SDK's request-body logger.
    names = {"openai", "openai._base_client", "httpx", "httpcore"}
    names.update(name for name in tuple(logging.Logger.manager.loggerDict)
                 if name.startswith(("openai.", "httpx.", "httpcore.")))
    for name in names:
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
        if not any(getattr(item, "_futurepath_private_transport", False) for item in logger.filters):
            logger.addFilter(_PrivateTransportLogs())


def _reasoning_parameter_unsupported(error: BadRequestError) -> bool:
    body = getattr(error, "body", None)
    if not isinstance(body, (dict, list)):
        return False
    text = json.dumps(body, ensure_ascii=True).casefold()
    return (
        "reasoning_effort" in text
        and any(term in text for term in ("unsupported", "unknown parameter", "unrecognized"))
    )


def _usage(response) -> LLMUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    input_tokens = getattr(usage, "prompt_tokens", None)
    output_tokens = getattr(usage, "completion_tokens", None)
    details = getattr(usage, "completion_tokens_details", None)
    reasoning_tokens = getattr(details, "reasoning_tokens", None) if details is not None else None
    if (type(input_tokens) is not int or input_tokens < 0
            or type(output_tokens) is not int or output_tokens < 0
            or (reasoning_tokens is not None
                and (type(reasoning_tokens) is not int or reasoning_tokens < 0))):
        return None
    return LLMUsage(input_tokens, output_tokens, reasoning_tokens)


class RunPodGLMProvider(LLMProvider):
    """Send one bounded Chat Completion to the fixed RunPod endpoint."""

    def __init__(self, api_key: str, *, client=None, allow_compatibility_retry: bool = True):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ProviderConfigurationError("RunPod API key is missing")
        if type(allow_compatibility_retry) is not bool:
            raise ProviderConfigurationError("Invalid RunPod retry configuration")
        self._allow_compatibility_retry = allow_compatibility_retry
        _suppress_payload_logging()
        self._client = client or OpenAI(
            api_key=api_key,
            base_url=RUNPOD_BASE_URL,
            timeout=20.0,
            max_retries=0,
        )
        _suppress_payload_logging()

    @classmethod
    def from_environment(cls, *, client=None, allow_compatibility_retry: bool = True) -> "RunPodGLMProvider":
        return cls(os.environ.get("RUNPOD_API_KEY", ""), client=client,
                   allow_compatibility_retry=allow_compatibility_retry)

    def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        if (request.feature not in {"career_advisor", "skill_gap_coach", "learning_roadmap", "career_chat"}
                or not isinstance(request.system_prompt, str)
                or not isinstance(request.user_prompt, str)
                or not request.system_prompt.strip()
                or not request.user_prompt.strip()
                or type(request.max_output_tokens) is not int
                or not 1 <= request.max_output_tokens <= MAX_OUTPUT_TOKENS
                or request.reasoning_effort not in SUPPORTED_REASONING_EFFORTS):
            raise ProviderFailure("invalid_request")
        if len(request.system_prompt.encode("utf-8")) + len(request.user_prompt.encode("utf-8")) > MAX_INPUT_BYTES:
            raise ProviderFailure("input_too_large")

        payload = {
            "model": RUNPOD_MODEL,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "max_tokens": request.max_output_tokens,
            "stream": False,
        }
        try:
            response = self._request(payload, request.reasoning_effort)
        except ProviderFailure:
            raise
        except APITimeoutError:
            raise ProviderFailure("timeout") from None
        except APIConnectionError:
            raise ProviderFailure("connection") from None
        except APIStatusError as error:
            status = error.status_code
            category = (
                "unauthorized" if status == 401 else
                "rate_limited" if status == 429 else
                "provider_unavailable" if status >= 500 else
                "provider_rejected_request" if status == 400 else
                "provider_error"
            )
            raise ProviderFailure(category, status) from None
        except Exception:
            raise ProviderFailure("provider_error") from None

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError):
            raise ProviderFailure("invalid_response") from None
        if not isinstance(content, str) or not content.strip():
            raise ProviderFailure("invalid_response")
        if len(content.encode("utf-8")) > 20_000:
            raise ProviderFailure("invalid_response")
        # The configured model is authoritative; do not log or propagate provider-controlled model text.
        return LLMCompletionResponse(content.strip(), _usage(response), RUNPOD_MODEL)

    def _request(self, payload: dict, reasoning_effort: str):
        try:
            return self._client.chat.completions.create(
                **payload,
                extra_body={"reasoning_effort": reasoning_effort},
            )
        except BadRequestError as error:
            if not self._allow_compatibility_retry or not _reasoning_parameter_unsupported(error):
                raise
            return self._client.chat.completions.create(**payload)
