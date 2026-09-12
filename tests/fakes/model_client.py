"""Deterministic test-only ModelClient implementation for future discovery tests."""

from __future__ import annotations

from capability_runner.discovery.model_client import ModelRequest, ModelResponse


class FakeModelClient:
    def __init__(self, responses: tuple[ModelResponse, ...]) -> None:
        self._responses = list(responses)
        self.requests: list[ModelRequest] = []

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("FakeModelClient has no queued response.")
        return self._responses.pop(0)
