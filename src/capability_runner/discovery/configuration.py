"""Trusted configuration and explicit provider composition for ModelClient."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from .model_client import ModelClient

ModelProvider = Literal["openai", "anthropic", "gemma"]


class ModelProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: ModelProvider
    model: str = Field(min_length=1, max_length=256)
    timeout_seconds: float = Field(default=30, gt=0, le=120)
    api_key: SecretStr | None = None
    base_url: str | None = None


class ModelConfigurationError(ValueError):
    pass


def load_model_provider_config(
    environment: Mapping[str, str] | None = None,
) -> ModelProviderConfig:
    values = os.environ if environment is None else environment
    provider = values.get("LLM_PROVIDER")
    if provider not in {"openai", "anthropic", "gemma"}:
        raise ModelConfigurationError("LLM_PROVIDER must be openai, anthropic, or gemma.")

    prefix = provider.upper()
    model = values.get(f"{prefix}_MODEL")
    if not model:
        raise ModelConfigurationError(f"{prefix}_MODEL is required.")
    api_key = values.get(f"{prefix}_API_KEY")
    if provider != "gemma" and not api_key:
        raise ModelConfigurationError(f"{prefix}_API_KEY is required.")

    base_url = values.get("GEMMA_BASE_URL") if provider == "gemma" else None
    if provider == "gemma" and not base_url:
        raise ModelConfigurationError("GEMMA_BASE_URL is required.")

    return ModelProviderConfig(
        provider=cast(ModelProvider, provider),
        model=model,
        api_key=SecretStr(api_key) if api_key else None,
        base_url=base_url,
    )


def create_model_client(config: ModelProviderConfig) -> ModelClient:
    if config.provider == "openai":
        from .providers.openai_client import OpenAIModelClient

        assert config.api_key is not None
        return OpenAIModelClient(config)
    if config.provider == "anthropic":
        from .providers.anthropic_client import AnthropicModelClient

        assert config.api_key is not None
        return AnthropicModelClient(config)
    from .providers.gemma_client import GemmaModelClient

    assert config.base_url is not None
    return GemmaModelClient(config)
