"""Explicitly injected test provider. Never enabled by deployment configuration."""
import json
from services.llm.provider import LLMCompletionResponse, LLMUsage, ProviderFailure


class MockLLMProvider:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        try:
            value = next(self.responses)
        except StopIteration:
            raise ProviderFailure('mock_exhausted') from None
        return LLMCompletionResponse(json.dumps(value), LLMUsage(0, 0), 'mock')
