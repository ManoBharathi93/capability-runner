# Model Providers

## Accepted boundary

Discovery uses a provider-neutral Model Client with OpenAI, Anthropic, and hosted Gemma adapters under `src/capability_runner/discovery/providers/`. Provider SDK types and wire formats remain inside the corresponding adapter. Replay must not import Model Client, provider adapters, or provider SDKs.

This provider set is **ACCEPTED BASELINE**. Feature compatibility and live availability are not **VERIFIED BEHAVIOR**.

## P3.1 status

P3.1 implements a provider-neutral `ModelClient` contract and explicit OpenAI, Anthropic, and Gemma-compatible HTTP adapters. It uses one shared `httpx` transport dependency; no provider SDK is installed and normal tests use mock transports only. The local deployment note in `docs/gemma-client.md` contains a deployment-specific endpoint and is ignored pending publication review. Public documentation uses `GEMMA_BASE_URL` rather than embedding that host.

## Configuration names

| Variable | Purpose | Persistence rule |
| --- | --- | --- |
| `LLM_PROVIDER` | Select the discovery adapter. | Nonsecret configuration. |
| `OPENAI_API_KEY` | Authenticate an OpenAI deployment. | Local secret; never commit or log. |
| `OPENAI_MODEL` | Select an OpenAI model/deployment. | Nonsecret unless deployment policy says otherwise. |
| `ANTHROPIC_API_KEY` | Authenticate an Anthropic deployment. | Local secret; never commit or log. |
| `ANTHROPIC_MODEL` | Select an Anthropic model. | Nonsecret unless deployment policy says otherwise. |
| `GEMMA_BASE_URL` | Select a hosted Gemma-compatible endpoint. | Deployment configuration; do not publish private hostnames. |
| `GEMMA_MODEL` | Select the hosted Gemma model/deployment. | Nonsecret unless deployment policy says otherwise. |
| `GEMMA_API_KEY` | Authenticate when the deployment requires it. | Local secret; never commit or log. |

`LLM_PROVIDER` explicitly selects exactly one adapter: `openai`, `anthropic`, or `gemma`. There is no automatic fallback. Each invocation has a bounded default timeout of 30 seconds, configurable only through trusted `ModelProviderConfig` composition. Adapters normalize failures to `AUTHENTICATION_ERROR`, `RATE_LIMITED`, `TIMEOUT`, `CONNECTION_ERROR`, `INVALID_RESPONSE`, or `PROVIDER_ERROR` without retaining request bodies, credentials, or raw provider objects.

Gemma uses only the documented OpenAI-compatible chat-completions shape at `${GEMMA_BASE_URL}/chat/completions`; P3.1 does not assume native structured-output enforcement, tool calling, image support, or any other provider-specific capability. `ModelClient` returns normalized text content which future Discovery code must parse and validate outside adapter SDK/wire formats. Replay remains isolated from this layer.

## Capability verification

Adapter implementation in P3.1 must distinguish contract tests from live deployment probes. For each configured provider/model, record separately:

- text and image input support required by the chosen discovery mode;
- tool calling or schema-constrained action output behavior;
- request and response size limits relevant to observations;
- timeout, rate-limit, refusal, malformed-output, and authentication mapping;
- sanitization of provider errors and usage metadata;
- exact model/deployment identifier and test date without credentials.

A compatible chat-completion path or endpoint name alone does not establish image, tool, audio, or structured-output support. Hosted Gemma behavior is deployment-specific.

## P3.1 implementation order

Define the smallest normalized Model Client contract from Discovery Engine needs, then implement and contract-test each adapter independently. Provider-specific extensions require explicit capability declarations rather than leaking vendor objects into shared contracts. Live status remains separate for OpenAI, Anthropic, and hosted Gemma.