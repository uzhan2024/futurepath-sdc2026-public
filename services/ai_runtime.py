"""Opt-in AI runtime construction, consent gate, and safe usage accounting."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
import os
import secrets

from services.ai_budget import (
    AIBudgetSettings,
    BudgetRejected,
    BudgetUnavailable,
    RedisAIBudgetGuard,
    log_usage,
)
from services.llm.provider import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    LLMProvider,
    ProviderFailure,
    ProviderConfigurationError,
)
from services.llm.runpod_glm import MAX_INPUT_BYTES, MAX_OUTPUT_TOKENS, RUNPOD_MODEL, SUPPORTED_REASONING_EFFORTS, RunPodGLMProvider


@dataclass(frozen=True)
class AIAvailability:
    configured: bool
    reason: str


@dataclass(frozen=True)
class AIGatewayResult:
    content: str
    usage: object
    model: str
    request_id: str
    estimated_cost_usd: Decimal
    latency_ms: float | None = None


class AIGatewayFailure(RuntimeError):
    """Safe failure category for presentation without provider exception details."""

    def __init__(self, category: str):
        super().__init__(category)
        self.category = category


def _enabled_flag() -> bool:
    return os.getenv("FUTUREPATH_AI_ENABLED", "false").strip().casefold() == "true"


def public_mode() -> bool:
    return os.getenv('FUTUREPATH_DEPLOYMENT_MODE', 'local').casefold() == 'public' or bool(os.getenv('REPL_ID') or os.getenv('REPLIT_DEPLOYMENT'))


def provider_choice() -> str:
    return os.getenv('FUTUREPATH_AI_PROVIDER', 'disabled' if public_mode() else 'ollama').strip().casefold()


def create_gateway(*, test_provider=None):
    choice = provider_choice()
    if choice == 'ollama' and not public_mode():
        from services.local_ai import LocalAIGateway
        try:
            return LocalAIGateway()
        except ProviderConfigurationError:
            raise AIGatewayFailure('provider_configuration_unavailable') from None
    if choice == 'mock' and test_provider is not None and not public_mode():
        from services.local_ai import LocalAIGateway
        return LocalAIGateway(test_provider)
    if choice == 'runpod':
        return AIGateway.from_environment()
    raise AIGatewayFailure('disabled')


def _reasoning_effort() -> str:
    return os.getenv("FUTUREPATH_AI_REASONING_EFFORT", "low").strip().casefold()


def ai_availability() -> AIAvailability:
    """Inspect safe configuration presence without contacting providers or Redis."""
    choice = provider_choice()
    if choice == 'ollama':
        if public_mode():
            return AIAvailability(False, 'local_provider_blocked')
        try:
            from services.llm.ollama import local_url
            local_url(os.getenv('FUTUREPATH_OLLAMA_URL', 'http://127.0.0.1:11434'))
        except (ValueError, ProviderConfigurationError):
            return AIAvailability(False, 'invalid_limit_configuration')
        return AIAvailability(True, 'local_configured')
    if choice != 'runpod' or not _enabled_flag():
        return AIAvailability(False, "disabled")
    if not os.getenv("RUNPOD_API_KEY", "").strip():
        return AIAvailability(False, "missing_provider_key")
    if not os.getenv("REDIS_URL", "").startswith("rediss://"):
        return AIAvailability(False, "shared_tls_budget_store_required")
    if _reasoning_effort() not in SUPPORTED_REASONING_EFFORTS:
        return AIAvailability(False, "invalid_limit_configuration")
    try:
        settings = AIBudgetSettings.from_environment()
    except BudgetUnavailable:
        return AIAvailability(False, "invalid_limit_configuration")
    if settings.max_input_bytes > MAX_INPUT_BYTES or settings.max_output_tokens > MAX_OUTPUT_TOKENS:
        return AIAvailability(False, "provider_request_limit_exceeded")
    return AIAvailability(True, "configured")


def new_session_id() -> str:
    """Generate a random per-browser identifier that is not sent to the model."""
    return secrets.token_urlsafe(32)


class AIGateway:
    def __init__(self, provider: LLMProvider, budget: RedisAIBudgetGuard, *,
                 max_output_tokens: int = MAX_OUTPUT_TOKENS, reasoning_effort: str = "low"):
        if (type(max_output_tokens) is not int or not 1 <= max_output_tokens <= MAX_OUTPUT_TOKENS
                or reasoning_effort not in SUPPORTED_REASONING_EFFORTS):
            raise AIGatewayFailure("invalid_limit_configuration")
        self._provider = provider
        self._budget = budget
        self._max_output_tokens = max_output_tokens
        self._reasoning_effort = reasoning_effort

    @classmethod
    def from_environment(cls) -> "AIGateway":
        availability = ai_availability()
        if not availability.configured:
            raise AIGatewayFailure(availability.reason)
        try:
            settings = AIBudgetSettings.from_environment()
            budget = RedisAIBudgetGuard.from_environment(settings)
            provider = RunPodGLMProvider.from_environment()
        except BudgetUnavailable as error:
            raise AIGatewayFailure(error.args[0]) from None
        except Exception:
            raise AIGatewayFailure("provider_configuration_unavailable") from None
        return cls(provider, budget, max_output_tokens=settings.max_output_tokens,
                   reasoning_effort=_reasoning_effort())

    def complete(self, request: LLMCompletionRequest, *, session_id: str, consented: bool) -> AIGatewayResult:
        if consented is not True:
            raise AIGatewayFailure("consent_required")
        if not isinstance(session_id, str) or not session_id:
            raise AIGatewayFailure("session_unavailable")
        if type(request.max_output_tokens) is not int or request.max_output_tokens < 1:
            raise AIGatewayFailure("request_size_limit")
        request = replace(request, max_output_tokens=min(request.max_output_tokens, self._max_output_tokens),
                          reasoning_effort=self._reasoning_effort)
        input_bytes = len(request.system_prompt.encode("utf-8")) + len(request.user_prompt.encode("utf-8"))
        if input_bytes > MAX_INPUT_BYTES:
            raise AIGatewayFailure("request_size_limit")

        try:
            reservation = self._budget.reserve(
                session_id=session_id,
                input_bytes=input_bytes,
                output_tokens=request.max_output_tokens,
            )
        except BudgetRejected as error:
            raise AIGatewayFailure(error.category) from None
        except BudgetUnavailable as error:
            raise AIGatewayFailure(error.args[0]) from None
        request_id = reservation.request_id

        try:
            result = self._provider.complete(request)
        except ProviderFailure as error:
            estimate = self._finalize_or_fail_closed(reservation, None)
            log_usage(
                request_id=request_id,
                feature=request.feature,
                model=RUNPOD_MODEL,
                usage=None,
                cost_usd=estimate.estimated_cost_usd,
                status=error.category,
            )
            raise AIGatewayFailure(error.category) from None
        except Exception:
            estimate = self._finalize_or_fail_closed(reservation, None)
            log_usage(
                request_id=request_id,
                feature=request.feature,
                model=RUNPOD_MODEL,
                usage=None,
                cost_usd=estimate.estimated_cost_usd,
                status="provider_error",
            )
            raise AIGatewayFailure("provider_error") from None

        usage = result.usage
        if usage is None:
            actual_cost = None
        else:
            actual_cost = self._budget.estimate_cost(
                usage.input_tokens, usage.output_tokens, usage.reasoning_tokens,
            )
        estimate = self._finalize_or_fail_closed(reservation, actual_cost)
        log_usage(
            request_id=request_id,
            feature=request.feature,
            model=result.model,
            usage=usage,
            cost_usd=estimate.estimated_cost_usd,
            status="success",
        )
        return AIGatewayResult(
            result.content, usage, result.model, request_id, estimate.estimated_cost_usd,
        )

    def _finalize_or_fail_closed(self, reservation, actual_cost):
        try:
            return self._budget.finalize(reservation, actual_cost)
        except Exception:
            # Reservation remains charged and its concurrency lease expires; never return content
            # when shared accounting could not record the provider outcome.
            raise AIGatewayFailure("usage_record_unavailable") from None
