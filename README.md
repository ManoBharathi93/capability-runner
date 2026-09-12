# Capability Runner

Capability Runner turns one genuine LLM-guided browser run into a typed, versioned capability and
then executes that capability deterministically without a model in the decision loop. The included
vertical slice operates a synthetic, read-only CoreBank application through real Chromium and
demonstrates successful discovery and replay, an expected business outcome, and same-session human
intervention.

The architectural principle is simple: the model may propose actions during Discovery, but every
automated or operator action is resolved through trusted semantic bindings, checked by policy, and
serialized by session ownership controls. Replay interprets only a validated saved artifact.

## Prerequisites

- CPython 3.12
- [`uv`](https://docs.astral.sh/uv/)
- Network access and a provider credential only for the live Discovery command

From the repository root:

```powershell
uv sync --all-groups
uv run playwright install chromium
```

The second command is required on a fresh machine; installing the Python Playwright package does
not install Chromium.

## Provider configuration

Only Discovery paths call a model: the CLI through-line, product Discovery, and explicitly live
evaluations. Copy [.env.example](.env.example) to `.env` or set the same variables in the process
environment. Process variables take precedence. Select exactly one
provider with `LLM_PROVIDER=openai`, `anthropic`, or `gemma`, then configure its matching group:

| Provider | Required configuration |
| --- | --- |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| Anthropic | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| Gemma-compatible HTTP | `GEMMA_BASE_URL`, `GEMMA_MODEL`, and `GEMMA_API_KEY` when required |

There is no silent provider fallback. Keep `.env` local; credentials, private endpoints, and raw
sensitive values must not be committed or placed in evidence. See [provider details](docs/providers.md).

## Run the end-to-end demo

```powershell
uv run capability-runner demo through-line
```

This command starts the local CoreBank surface, asks the configured model to discover the fixed
goal "Find the savings balance for member 67890," compiles and stores the verified trace, destroys
the Discovery browser/control session, then loads the generated artifact into a fresh Replay
session with a different input. A successful run reports:

- Discovery `SUCCESS` and its model-call count;
- `lookup_savings_balance@1.0.0` stored as versioned JSON;
- fresh Replay `SUCCESS` with `438221` minor units and `USD`;
- zero model calls from Capability Builder and Replay.

Runtime files are written to `var/demo-runs/<run-id>/`. Use `--output-root PATH` to choose another
root. The command exits nonzero if configuration, execution, or its expected-result checks fail.

## Run without a model

The remaining reviewer paths require no provider credentials:

```powershell
uv run capability-runner demo intervention
uv run capability-runner demo exception
```

`intervention` pauses Replay at `APPROVAL_REQUIRED`, performs the approved action through the local
operator HTTP path on the same live browser session, validates fresh state, advances the control
generation, and resumes without repeating prior actions. `exception` replays the bundled
capability for an unknown synthetic member and returns `BUSINESS_OUTCOME / MEMBER_NOT_FOUND`
instead of misclassifying that domain result as a crash.

Command help is available with:

```powershell
uv run capability-runner --help
uv run capability-runner demo --help
```

## Run the product frontend

The product surface is the clearest reviewer path; the CLI commands remain the shortest reproducible
evidence path. Both use the same Discovery, Replay, policy, and same-session intervention behavior.

Install and build the client once, then start the full product:

```powershell
npm --prefix web ci
npm --prefix web run build
uv run capability-runner serve
```

Open `http://127.0.0.1:5000/` for the production-built client. For frontend development, keep the
product server running and start Vite in a second terminal:

```powershell
npm --prefix web run dev
```

Then open `http://127.0.0.1:5173/`. Vite proxies `/api` to the local product server. Discovery uses
the configured provider; Replay and intervention paths are model-free. The Teach route is a disabled
visual shell; voice and screen-share behavior is not implemented.

## Evidence

The curated [evidence package](evidence/README.md) contains unmodified files from actual executions:

- a generated capability plus combined Discovery and fresh-Replay JSONL from the verified live
	through-line;
- a model-free not-found summary and JSONL;
- bounded visible-state evidence from a genuine session-expired Replay failure.

Runtime output under `var/` is working data. The checked-in `evidence/` selection is the reviewed,
sanitized submission record.

## Checks

Ordinary tests exclude the opt-in live provider cases:

```powershell
uv run pytest -q
uv run ruff check .
uv run pyright
uv lock --check
```

Run the public live acceptance only with valid provider configuration:

```powershell
uv run pytest tests/live/demo/test_demo_through_line.py -m live -q
```

The latest recorded baseline is 371 ordinary tests passed, 8 live tests deselected, 7 frontend
tests passed, the TypeScript check and Vite build passed, Ruff passed, Pyright reported no errors
or warnings, and the Python dependency lock remained unchanged. See [progress](docs/progress.md) for
dated evidence rather than treating this statement as a substitute for a local run.

## Design boundaries

The implementation is deliberately a local modular monolith with one Playwright browser adapter,
two synthetic banking applications, trusted or generated profiles, local JSON storage, and
process-local intervention state. The
surface protocol and semantic targets describe how legacy web or desktop adapters could fit, and
application/variant profiles describe tenant specialization, but neither a second surface nor a
multi-tenant runtime is implemented. The local operator page is unauthenticated and is not a
production deployment surface. Redaction is key- and exact-value-based rather than general PII
detection. Replay lifecycle and sanitized intervention context are persisted; Discovery emits
sanitized lifecycle and decision-classification metadata. The curated provider-backed through-line
proves that complete chronology without persisting raw model content or sensitive invocation values.

Read [REPORT.md](REPORT.md) for the decisions and trade-offs, [system design](docs/submission/system-design.md)
for component-level flow, and [requirement traceability](docs/submission/requirement-traceability.md)
for the assignment-by-assignment audit.

## Generic browser Discovery and live workspace

Profile-less Discovery supports previously unseen web applications within the current Browser
Surface capabilities. This is the bounded implementation scope; actual live acceptance and limits
are recorded in [progress](docs/progress.md). It is not a claim to work on every website.

```sh
uv sync
uv run playwright install chromium
npm --prefix web ci
npm --prefix web run build
uv run capability-runner serve
```

Configure the chosen provider in `.env` first. Open `http://127.0.0.1:5000/discover`. Choose CoreBank's
known profile, either banking application in new-app mode, or an explicitly allowlisted sandbox URL.
Enter any nonempty bounded goal, watch the same managed browser, inspect the typed capability and
separate binding, then replay with another input. Replay has no model fallback.

See the [browser contract](docs/submission/generic-browser-scope.md),
[manual tests](docs/submission/manual-test-guide.md),
[reviewer video walkthrough](docs/submission/demo-walkthrough.md), and [evaluation commands](evals/README.md).
Generated packages and reports remain local; active run/session state is process-local.
