"""Fail-closed, Redis-backed shared request and estimated-cost enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import hashlib
import logging
import os
import re
import secrets
from urllib.parse import urlsplit

from redis import Redis
from redis.exceptions import RedisError


logger = logging.getLogger("futurepath.ai.usage")
MICROS_PER_USD = Decimal(1_000_000)
PROMPT_OVERHEAD_TOKENS = 512
REASONING_OUTPUT_RESERVE_MULTIPLIER = 2
LEASE_SECONDS = 90
COUNTER_TTL_SECONDS = 3 * 24 * 60 * 60
REDIS_HASH_TAG = "{futurepath-ai}"


class BudgetUnavailable(RuntimeError):
    """The shared limit service cannot safely authorize another model request."""


class BudgetRejected(RuntimeError):
    """The shared request, cost, session, or concurrency limit was reached."""

    def __init__(self, category: str):
        super().__init__(category)
        self.category = category


@dataclass(frozen=True)
class AIBudgetSettings:
    daily_budget_usd: Decimal = Decimal("0.10")
    daily_request_limit: int = 10
    session_request_limit: int = 3
    max_concurrent: int = 1
    max_input_bytes: int = 8_000
    max_output_tokens: int = 512
    input_usd_per_million: Decimal = Decimal("0.77")
    output_usd_per_million: Decimal = Decimal("2.42")

    @classmethod
    def from_environment(cls) -> "AIBudgetSettings":
        try:
            settings = cls(
                daily_budget_usd=Decimal(os.getenv("FUTUREPATH_AI_DAILY_BUDGET_USD", "0.10")),
                daily_request_limit=int(os.getenv("FUTUREPATH_AI_DAILY_REQUEST_LIMIT", "10")),
                session_request_limit=int(os.getenv("FUTUREPATH_AI_SESSION_REQUEST_LIMIT", "3")),
                max_concurrent=int(os.getenv("FUTUREPATH_AI_MAX_CONCURRENT", "1")),
                max_input_bytes=int(os.getenv("FUTUREPATH_AI_MAX_INPUT_BYTES", "8000")),
                max_output_tokens=int(os.getenv("FUTUREPATH_AI_MAX_OUTPUT_TOKENS", "512")),
                input_usd_per_million=Decimal(os.getenv("FUTUREPATH_AI_INPUT_USD_PER_MILLION", "0.77")),
                output_usd_per_million=Decimal(os.getenv("FUTUREPATH_AI_OUTPUT_USD_PER_MILLION", "2.42")),
            )
        except (InvalidOperation, TypeError, ValueError):
            raise BudgetUnavailable("invalid_limit_configuration") from None
        settings.validate()
        return settings

    def validate(self) -> None:
        if (not self.daily_budget_usd.is_finite() or self.daily_budget_usd <= 0
                or not self.input_usd_per_million.is_finite() or self.input_usd_per_million <= 0
                or not self.output_usd_per_million.is_finite() or self.output_usd_per_million <= 0):
            raise BudgetUnavailable("invalid_limit_configuration")
        if not 1 <= self.daily_request_limit <= 10_000:
            raise BudgetUnavailable("invalid_limit_configuration")
        if not 1 <= self.session_request_limit <= self.daily_request_limit:
            raise BudgetUnavailable("invalid_limit_configuration")
        if not 1 <= self.max_concurrent <= 32:
            raise BudgetUnavailable("invalid_limit_configuration")
        if not 512 <= self.max_input_bytes <= 12_000:
            raise BudgetUnavailable("invalid_limit_configuration")
        if not 1 <= self.max_output_tokens <= 512:
            raise BudgetUnavailable("invalid_limit_configuration")


@dataclass(frozen=True)
class Reservation:
    request_id: str
    day_key: str
    session_key: str
    reserved_micros: int


@dataclass(frozen=True)
class UsageEstimate:
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: Decimal
    charged_at_reservation_ceiling: bool


RESERVE_SCRIPT = r"""
-- futurepath-ai-reserve-v1
local now = tonumber(ARGV[1])
local expiry = tonumber(ARGV[2])
local request_limit = tonumber(ARGV[3])
local session_limit = tonumber(ARGV[4])
local max_active = tonumber(ARGV[5])
local reserved_cost = tonumber(ARGV[6])
local daily_budget = tonumber(ARGV[7])
local request_ttl = tonumber(ARGV[8])
redis.call('ZREMRANGEBYSCORE', KEYS[3], '-inf', now)
local request_count = tonumber(redis.call('GET', KEYS[1]) or '0')
local session_count = tonumber(redis.call('GET', KEYS[4]) or '0')
local spent = tonumber(redis.call('GET', KEYS[2]) or '0')
if request_count >= request_limit then return {0, 'daily_request_limit'} end
if session_count >= session_limit then return {0, 'session_request_limit'} end
if spent + reserved_cost > daily_budget then return {0, 'daily_budget_limit'} end
if redis.call('ZCARD', KEYS[3]) >= max_active then return {0, 'concurrency_limit'} end
redis.call('INCR', KEYS[1])
redis.call('INCR', KEYS[4])
redis.call('INCRBY', KEYS[2], reserved_cost)
redis.call('EXPIRE', KEYS[1], request_ttl)
redis.call('EXPIRE', KEYS[2], request_ttl)
redis.call('EXPIRE', KEYS[4], request_ttl)
redis.call('ZADD', KEYS[3], expiry, ARGV[9])
redis.call('EXPIRE', KEYS[3], request_ttl)
return {1, request_count + 1, session_count + 1, spent + reserved_cost}
"""


FINALIZE_SCRIPT = r"""
-- futurepath-ai-finalize-v1
local reserved = tonumber(ARGV[1])
local actual = tonumber(ARGV[2])
redis.call('ZREM', KEYS[1], ARGV[3])
if actual < reserved then
  local current = tonumber(redis.call('GET', KEYS[2]) or '0')
  local refund = reserved - actual
  if current <= refund then redis.call('SET', KEYS[2], 0)
  else redis.call('DECRBY', KEYS[2], refund) end
elseif actual > reserved then
  redis.call('INCRBY', KEYS[2], actual - reserved)
end
return 1
"""


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _micros(value: Decimal) -> int:
    return int((value * MICROS_PER_USD).to_integral_value(rounding=ROUND_CEILING))


class RedisAIBudgetGuard:
    """Use Redis Lua transactions so every replica shares the same safety limits."""

    def __init__(self, client: Redis, settings: AIBudgetSettings):
        self._client = client
        self._settings = settings
        settings.validate()

    @classmethod
    def from_environment(cls, settings: AIBudgetSettings | None = None) -> "RedisAIBudgetGuard":
        url = os.getenv("REDIS_URL", "")
        if not url or not url.startswith("rediss://"):
            raise BudgetUnavailable("shared_tls_redis_required")
        if not re.match(r"^rediss://[^\s]+$", url):
            raise BudgetUnavailable("invalid_shared_store_configuration")
        try:
            parsed = urlsplit(url)
            if not parsed.hostname or parsed.query or parsed.fragment:
                # redis-py URL query options override explicit kwargs, including
                # TLS verification and timeouts. The guard accepts only the
                # credentials/host/port/database URL contract.
                raise ValueError("Redis URL options are not accepted")
            client = Redis.from_url(
                url,
                decode_responses=False,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
                retry_on_timeout=False,
                health_check_interval=10,
                ssl_cert_reqs="required",
                ssl_check_hostname=True,
            )
            client.ping()
        except RedisError:
            raise BudgetUnavailable("shared_store_unavailable") from None
        except Exception:
            raise BudgetUnavailable("invalid_shared_store_configuration") from None
        return cls(client, settings or AIBudgetSettings.from_environment())

    def reserve(self, *, session_id: str, input_bytes: int, output_tokens: int) -> Reservation:
        settings = self._settings
        if not isinstance(session_id, str) or not session_id or type(input_bytes) is not int or input_bytes < 0:
            raise BudgetRejected("invalid_request")
        if input_bytes > settings.max_input_bytes or type(output_tokens) is not int or not 1 <= output_tokens <= settings.max_output_tokens:
            raise BudgetRejected("request_size_limit")

        input_token_ceiling = input_bytes + PROMPT_OVERHEAD_TOKENS
        output_token_ceiling = output_tokens * REASONING_OUTPUT_RESERVE_MULTIPLIER
        reserve_usd = (
            Decimal(input_token_ceiling) * settings.input_usd_per_million
            + Decimal(output_token_ceiling) * settings.output_usd_per_million
        ) / MICROS_PER_USD
        reserve_micros = _micros(reserve_usd)
        budget_micros = _micros(settings.daily_budget_usd)
        day = _utc_day()
        session_digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        request_id = secrets.token_hex(16)
        prefix = f"futurepath:ai:{REDIS_HASH_TAG}"
        keys = [
            f"{prefix}:{day}:requests",
            f"{prefix}:{day}:reserved_usd_micros",
            f"{prefix}:active",
            f"{prefix}:{day}:session:{session_digest}:requests",
        ]
        now = int(datetime.now(timezone.utc).timestamp())
        args = [
            now,
            now + LEASE_SECONDS,
            settings.daily_request_limit,
            settings.session_request_limit,
            settings.max_concurrent,
            reserve_micros,
            budget_micros,
            COUNTER_TTL_SECONDS,
            request_id,
        ]
        try:
            result = self._client.eval(RESERVE_SCRIPT, len(keys), *keys, *args)
        except (RedisError, OSError):
            raise BudgetUnavailable("shared_store_unavailable") from None
        except Exception:
            raise BudgetUnavailable("shared_store_unavailable") from None
        if not isinstance(result, (list, tuple)) or not result:
            raise BudgetUnavailable("shared_store_invalid_response")
        if int(result[0]) != 1:
            category = result[1].decode("ascii", "ignore") if isinstance(result[1], bytes) else str(result[1])
            raise BudgetRejected(category)
        return Reservation(request_id, day, session_digest, reserve_micros)

    def finalize(self, reservation: Reservation, actual_cost_usd: Decimal | None) -> UsageEstimate:
        charged_ceiling = actual_cost_usd is None
        actual_micros = reservation.reserved_micros if charged_ceiling else _micros(actual_cost_usd)
        actual_micros = max(0, actual_micros)
        prefix = f"futurepath:ai:{REDIS_HASH_TAG}"
        active_key = f"{prefix}:active"
        cost_key = f"{prefix}:{reservation.day_key}:reserved_usd_micros"
        try:
            self._client.eval(
                FINALIZE_SCRIPT, 2, active_key, cost_key,
                reservation.reserved_micros, actual_micros, reservation.request_id,
            )
        except (RedisError, OSError):
            raise BudgetUnavailable("usage_record_unavailable") from None
        except Exception:
            raise BudgetUnavailable("usage_record_unavailable") from None
        return UsageEstimate(None, None, Decimal(actual_micros) / MICROS_PER_USD, charged_ceiling)

    def estimate_cost(self, input_tokens: int, output_tokens: int, reasoning_tokens: int | None = None) -> Decimal:
        if (type(input_tokens) is not int or input_tokens < 0
                or type(output_tokens) is not int or output_tokens < 0
                or (reasoning_tokens is not None
                    and (type(reasoning_tokens) is not int or reasoning_tokens < 0))):
            raise ValueError("invalid usage values")
        # Chat Completions completion_tokens already includes its reasoning-token subset.
        billable_output = output_tokens
        raw = (
            Decimal(input_tokens) * self._settings.input_usd_per_million
            + Decimal(billable_output) * self._settings.output_usd_per_million
        ) / MICROS_PER_USD
        return Decimal(_micros(raw)) / MICROS_PER_USD


def log_usage(*, request_id: str, feature: str, model: str, usage, cost_usd: Decimal, status: str) -> None:
    """Write minimal aggregate telemetry. Never pass prompt or response text here."""
    input_tokens = usage.input_tokens if usage is not None else "unknown"
    output_tokens = usage.output_tokens if usage is not None else "unknown"
    logger.info(
        "ai_usage request_id=%s feature=%s model=%s input_tokens=%s output_tokens=%s estimated_cost_usd=%s status=%s",
        request_id, feature, model, input_tokens, output_tokens, format(cost_usd, "f"), status,
    )
