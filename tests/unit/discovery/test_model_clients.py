from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from capability_runner.discovery.configuration import (
    ModelConfigurationError,
    ModelProvider,
    ModelProviderConfig,
    create_model_client,
    load_model_provider_config,
)
from capability_runner.discovery.model_client import (
    ModelClientError,
    ModelMessage,
    ModelRequest,
    ModelResponse,
)
from capability_runner.discovery.providers.anthropic_client import AnthropicModelClient
from capability_runner.discovery.providers.gemma_client import GemmaModelClient
from capability_runner.discovery.providers.openai_client import OpenAIModelClient
from tests.fakes.model_client import FakeModelClient

SENTINEL = "MODEL_PRIVATE_KEY_91827"
ProviderAdapter = type[OpenAIModelClient | AnthropicModelClient | GemmaModelClient]
MalformedCase = tuple[ProviderAdapter, ModelProviderConfig, dict[str, object]]


def _request() -> ModelRequest:
    return ModelRequest(
        messages=(
            ModelMessage(role="SYSTEM", content="Follow the provided schema."),
            ModelMessage(role="USER", content="Inspect this bounded observation."),
        ),
        max_tokens=64,
    )


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _config(provider: ModelProvider, *, base_url: str | None = None) -> ModelProviderConfig:
    return ModelProviderConfig(
        provider=provider,
        model="test-model",
        api_key=SecretStr(SENTINEL),
        base_url=base_url,
        timeout_seconds=5,
    )


def test_model_contracts_are_immutable_and_validate_messages() -> None:
    response = ModelResponse(content='{"kind":"ACT"}', provider="test", model="test-model")

    with pytest.raises(ValidationError):
        ModelRequest(messages=())

    assert response.content == '{"kind":"ACT"}'


def test_fake_model_client_returns_queued_responses_and_records_requests() -> None:
    async def scenario() -> None:
        request = _request()
        expected = ModelResponse(content="decision", provider="fake", model="fake-model")
        client = FakeModelClient((expected,))

        assert await client.complete(request) == expected
        assert client.requests == [request]
        with pytest.raises(AssertionError, match="no queued response"):
            await client.complete(request)

    asyncio.run(scenario())


def test_openai_translates_request_and_normalizes_response() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url == "https://api.openai.com/v1/chat/completions"
            assert request.headers["authorization"] == f"Bearer {SENTINEL}"
            assert json.loads(request.content) == {
                "model": "test-model",
                "messages": [
                    {"role": "system", "content": "Follow the provided schema."},
                    {"role": "user", "content": "Inspect this bounded observation."},
                ],
                "temperature": 0,
                "max_tokens": 64,
            }
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": '{"kind":"ACT"}'}}],
                    "usage": {"prompt_tokens": 11},
                },
            )

        response = await OpenAIModelClient(_config("openai"), client=_client(handler)).complete(
            _request()
        )
        assert response == ModelResponse(
            content='{"kind":"ACT"}',
            provider="openai",
            model="test-model",
            usage={"prompt_tokens": 11},
        )

    asyncio.run(scenario())


def test_anthropic_translates_request_and_normalizes_response() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url == "https://api.anthropic.com/v1/messages"
            assert request.headers["x-api-key"] == SENTINEL
            assert json.loads(request.content) == {
                "model": "test-model",
                "system": "Follow the provided schema.",
                "messages": [{"role": "user", "content": "Inspect this bounded observation."}],
                "temperature": 0,
                "max_tokens": 64,
            }
            return httpx.Response(200, json={"content": [{"text": '{"kind":"ACT"}'}]})

        response = await AnthropicModelClient(
            _config("anthropic"), client=_client(handler)
        ).complete(_request())
        assert response.content == '{"kind":"ACT"}'
        assert response.provider == "anthropic"

    asyncio.run(scenario())


def test_gemma_uses_configured_openai_compatible_endpoint() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url == "http://gemma.test/v1/chat/completions"
            assert request.headers["authorization"] == f"Bearer {SENTINEL}"
            assert json.loads(request.content)["messages"][1]["role"] == "user"
            return httpx.Response(200, json={"choices": [{"message": {"content": "decision"}}]})

        response = await GemmaModelClient(
            _config("gemma", base_url="http://gemma.test/v1/"), client=_client(handler)
        ).complete(_request())
        assert response == ModelResponse(content="decision", provider="gemma", model="test-model")

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("adapter", "config", "response", "code"),
    [
        (OpenAIModelClient, _config("openai"), httpx.Response(401), "AUTHENTICATION_ERROR"),
        (AnthropicModelClient, _config("anthropic"), httpx.Response(429), "RATE_LIMITED"),
        (
            GemmaModelClient,
            _config("gemma", base_url="http://gemma.test/v1"),
            httpx.Response(500),
            "PROVIDER_ERROR",
        ),
    ],
)
def test_provider_http_failures_are_normalized_and_redacted(
    adapter: type[OpenAIModelClient | AnthropicModelClient | GemmaModelClient],
    config: ModelProviderConfig,
    response: httpx.Response,
    code: str,
) -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return response

        with pytest.raises(ModelClientError) as captured:
            await adapter(config, client=_client(handler)).complete(_request())
        assert captured.value.code == code
        assert SENTINEL not in str(captured.value)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("adapter", "config", "failure", "expected_code"),
    [
        (OpenAIModelClient, _config("openai"), httpx.ReadTimeout("timed out"), "TIMEOUT"),
        (AnthropicModelClient, _config("anthropic"), httpx.ReadTimeout("timed out"), "TIMEOUT"),
        (
            GemmaModelClient,
            _config("gemma", base_url="http://gemma.test/v1"),
            httpx.ConnectError("offline"),
            "CONNECTION_ERROR",
        ),
    ],
)
def test_provider_transport_failures_are_normalized(
    adapter: ProviderAdapter,
    config: ModelProviderConfig,
    failure: httpx.RequestError,
    expected_code: str,
) -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise failure

        with pytest.raises(ModelClientError) as captured:
            await adapter(config, client=_client(handler)).complete(_request())
        assert captured.value.code == expected_code
        assert SENTINEL not in str(captured.value)

    asyncio.run(scenario())


def test_gemma_malformed_json_is_rejected() -> None:
    async def scenario() -> None:
        with pytest.raises(ModelClientError) as captured:
            await GemmaModelClient(
                _config("gemma", base_url="http://gemma.test/v1"),
                client=_client(lambda request: httpx.Response(200, content=b"not-json")),
            ).complete(_request())
        assert captured.value.code == "INVALID_RESPONSE"

    asyncio.run(scenario())


MALFORMED_CASES: tuple[MalformedCase, ...] = (
    (OpenAIModelClient, _config("openai"), {"choices": []}),
    (AnthropicModelClient, _config("anthropic"), {"content": [{"text": ""}]}),
    (GemmaModelClient, _config("gemma", base_url="http://gemma.test/v1"), {"choices": [{}]}),
)


@pytest.mark.parametrize(("adapter", "config", "payload"), MALFORMED_CASES)
def test_provider_malformed_content_is_rejected(
    adapter: ProviderAdapter,
    config: ModelProviderConfig,
    payload: dict[str, object],
) -> None:
    async def scenario() -> None:
        with pytest.raises(ModelClientError) as captured:
            await adapter(
                config, client=_client(lambda request: httpx.Response(200, json=payload))
            ).complete(_request())
        assert captured.value.code == "INVALID_RESPONSE"

    asyncio.run(scenario())


def test_explicit_factory_selection_has_no_fallback_and_redacts_credentials() -> None:
    config = load_model_provider_config(
        {
            "LLM_PROVIDER": "openai",
            "OPENAI_MODEL": "test-model",
            "OPENAI_API_KEY": SENTINEL,
        }
    )

    assert isinstance(create_model_client(config), OpenAIModelClient)
    assert SENTINEL not in repr(config)
    with pytest.raises(ModelConfigurationError):
        load_model_provider_config({"LLM_PROVIDER": "unsupported"})
    with pytest.raises(ModelConfigurationError):
        load_model_provider_config({"LLM_PROVIDER": "anthropic", "ANTHROPIC_MODEL": "test-model"})
