"""Local resource guard. It is intentionally not an Autoscale spending guard."""
from collections import OrderedDict
from decimal import Decimal
import hashlib
import threading
import time

from services.ai_runtime import AIGatewayFailure, AIGatewayResult
from services.llm.ollama import OllamaProvider
from services.llm.provider import ProviderFailure

_lock = threading.Lock()
_slot = threading.BoundedSemaphore(1)
_sessions = OrderedDict()


class LocalAIGateway:
    is_local = True

    def __init__(self, provider=None):
        self.provider = provider or OllamaProvider.from_environment()

    def complete(self, request, *, session_id, consented):
        from services.ai_runtime import public_mode
        if public_mode():
            raise AIGatewayFailure('local_provider_blocked')
        if consented is not True or not session_id:
            raise AIGatewayFailure('consent_required')
        if not _slot.acquire(blocking=False):
            raise AIGatewayFailure('concurrency_limit')
        try:
            key = hashlib.sha256(session_id.encode()).hexdigest()
            now = time.monotonic()
            with _lock:
                count, expiry = _sessions.pop(key, (0, now + 900))
                if now >= expiry:
                    count, expiry = 0, now + 900
                _sessions[key] = (count + 1, expiry)
                while len(_sessions) > 1000:
                    _sessions.popitem(last=False)
                if count >= 50:
                    raise AIGatewayFailure('session_request_limit')
            try:
                response = self.provider.complete(request)
            except ProviderFailure as error:
                raise AIGatewayFailure(error.category) from None
            except Exception:
                raise AIGatewayFailure('provider_error') from None
            return AIGatewayResult(response.content, response.usage, response.model, 'local-request', Decimal('0'), response.latency_ms)
        finally:
            _slot.release()
