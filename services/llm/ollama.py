"""Bounded, loopback-only Ollama transport; no download or cloud routing."""
from __future__ import annotations

import json
import os
import re
import time
from urllib.parse import urlsplit

import httpx

from services.llm.provider import LLMCompletionRequest, LLMCompletionResponse, LLMUsage, ProviderConfigurationError, ProviderFailure

DEFAULT_MODEL = 'qwen3.5:4b'
MAX_INPUT_BYTES = 6000
MAX_OUTPUT_TOKENS = 1536


def local_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == 'http' and parts.hostname in {'127.0.0.1', '::1'} and parts.port is not None
                 and not parts.username and not parts.password and parts.path in {'', '/'} and not parts.query and not parts.fragment)
    except ValueError:
        valid = False
    if not valid:
        raise ProviderConfigurationError('Ollama requires an explicit HTTP loopback address and port')
    return value.rstrip('/')


class OllamaProvider:
    def __init__(self, model=DEFAULT_MODEL, base_url='http://127.0.0.1:11434', *, client=None, timeout=60):
        self.base_url = local_url(base_url)
        if not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,100}', model) or 'cloud' in model.casefold() or '://' in model:
            raise ProviderConfigurationError('Choose an installed local model')
        if not 1 <= timeout <= 120:
            raise ProviderConfigurationError('Invalid local timeout')
        self.model = model
        self.client = client or httpx.Client(timeout=httpx.Timeout(timeout, connect=2), trust_env=False, follow_redirects=False)

    @classmethod
    def from_environment(cls):
        return cls(os.getenv('FUTUREPATH_OLLAMA_MODEL', DEFAULT_MODEL), os.getenv('FUTUREPATH_OLLAMA_URL', 'http://127.0.0.1:11434'))

    def _json(self, method, path, payload=None, maximum=160_000):
        try:
            with self.client.stream(method, self.base_url + path, json=payload) as response:
                if response.status_code != 200:
                    raise ProviderFailure('missing_model' if response.status_code == 404 else 'provider_unavailable')
                data = bytearray()
                for part in response.iter_bytes():
                    data.extend(part)
                    if len(data) > maximum:
                        raise ProviderFailure('invalid_response')
            return json.loads(data)
        except httpx.TimeoutException:
            raise ProviderFailure('timeout') from None
        except (httpx.HTTPError, OSError):
            raise ProviderFailure('provider_unavailable') from None
        except (json.JSONDecodeError, UnicodeError, TypeError):
            raise ProviderFailure('invalid_response') from None

    def models(self):
        value = self._json('GET', '/api/tags', maximum=100_000)
        if not isinstance(value, dict) or not isinstance(value.get('models'), list):
            raise ProviderFailure('invalid_response')
        return tuple(m['name'] for m in value['models'] if isinstance(m, dict) and isinstance(m.get('name'), str)
                     and 'cloud' not in m['name'].casefold() and not m.get('remote_host') and not m.get('remote_model'))

    def complete(self, request: LLMCompletionRequest):
        if len((request.system_prompt + request.user_prompt).encode()) + len(json.dumps(request.response_schema or {}).encode()) > MAX_INPUT_BYTES:
            raise ProviderFailure('request_size_limit')
        if type(request.max_output_tokens) is not int or not 1 <= request.max_output_tokens <= MAX_OUTPUT_TOKENS:
            raise ProviderFailure('request_size_limit')
        if self.model not in self.models():
            raise ProviderFailure('missing_model')
        started = time.monotonic()
        value = self._json('POST', '/api/chat', {
            'model': self.model, 'messages': [{'role': 'system', 'content': request.system_prompt},
                                            {'role': 'user', 'content': request.user_prompt}],
            'stream': False, 'think': False, 'format': request.response_schema or 'json', 'keep_alive': '2m',
            'options': {'temperature': 0, 'num_ctx': 8192, 'num_predict': request.max_output_tokens},
        })
        try:
            content = value['message']['content']
            if value.get('done') is not True or value.get('done_reason') == 'length' or not isinstance(content, str) or len(content.encode()) > 20_000:
                raise ValueError
            counts = [value.get('prompt_eval_count'), value.get('eval_count')]
            usage = LLMUsage(*counts) if all(type(x) is int and x >= 0 for x in counts) else None
            return LLMCompletionResponse(content, usage, self.model, (time.monotonic() - started) * 1000)
        except (KeyError, TypeError, ValueError):
            raise ProviderFailure('invalid_response') from None
