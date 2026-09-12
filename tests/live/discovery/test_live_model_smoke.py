from __future__ import annotations

from pathlib import Path

import pytest

from capability_runner.discovery.configuration import (
    create_model_client,
    load_model_provider_config,
)
from capability_runner.discovery.model_client import ModelMessage, ModelRequest


def _local_environment() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in Path(".env").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"').strip("'")
    return values


@pytest.mark.live
def test_configured_model_client_live_smoke() -> None:
    async def scenario() -> None:
        config = load_model_provider_config(_local_environment())
        client = create_model_client(config)
        response = await client.complete(
            ModelRequest(
                messages=(
                    ModelMessage(
                        role="USER",
                        content="Return exactly the word DISCOVERY_MODEL_OK.",
                    ),
                ),
                temperature=0,
                max_tokens=32,
            )
        )

        print(f"live provider={response.provider} model={response.model}")
        assert response.content.strip() == "DISCOVERY_MODEL_OK"

    import asyncio

    asyncio.run(scenario())