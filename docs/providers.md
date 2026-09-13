# Model provider setup

**Only Discovery needs a model.** Replay and the handoff demo run without a key.
Use [README setup](../README.md#provider-configuration) to configure one provider.

## Configuration

| Provider selection | Required values |
| --- | --- |
| `LLM_PROVIDER=openai` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `LLM_PROVIDER=anthropic` | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| `LLM_PROVIDER=gemma` | `GEMMA_BASE_URL`, `GEMMA_MODEL`; `GEMMA_API_KEY` when required |

Copy [.env.example](../.env.example) to a local `.env`.
Process environment values take precedence. No automatic provider fallback occurs.
Keep credentials and private endpoints out of Git, evidence and recordings.

## Why the adapters are separate

Discovery uses a shared Model Client contract. Each adapter translates that
contract into its provider's HTTP format. Provider-specific objects stay inside
the adapter. Replay cannot import this layer.

The implementation uses `httpx`, not provider SDKs. Gemma expects an
OpenAI-compatible `/chat/completions` endpoint. That protocol alone does not
prove tool calling, image, audio or strict structured-output support.

## When a call fails

| Reason | Check |
| --- | --- |
| `AUTHENTICATION_ERROR` | Credential and access to the configured model. |
| `RATE_LIMITED` | Provider quota or rate limit. |
| `TIMEOUT` | Provider response time; the default call timeout is 30 seconds. |
| `CONNECTION_ERROR` | Reachability of the configured endpoint. |
| `INVALID_RESPONSE` | Compatibility with the adapter's expected response format. |
| `PROVIDER_ERROR` | Provider availability and configuration. |

Errors are normalized without keeping raw provider payloads or credentials.
Timeout changes belong in trusted backend configuration.

## What has been tested

Mock HTTP tests check request formatting and failure mapping. Recorded real-model
runs establish only the provider/deployment used in those runs, not equal
reliability across all three providers. See [progress](progress.md).

The provider boundary is **ACCEPTED BASELINE**. Completed checks are
**VERIFIED BEHAVIOR** only when evidence is recorded. New provider features need
their own compatibility checks.
