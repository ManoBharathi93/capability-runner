# Capability Runner

Turn a natural-language goal into a saved browser workflow, then run it again
with new inputs **without calling a model**.

The demo uses two local banking apps with synthetic data. It supports savings
and checking enquiries, expected errors, and human takeover of a paused browser.

**Start with [the screenshot guide](docs/submission/test-product.md).**
Read [REPORT.md](REPORT.md) for decisions and [evidence](evidence/README.md)
for recorded results. Use the [documentation map](docs/README.md) for more detail.

## Setup

You need Python 3.12, [uv](https://docs.astral.sh/uv/), and Node.js/npm.
Run these commands from the repository root:

```powershell
uv sync --all-groups
uv run playwright install chromium
npm --prefix web ci
npm --prefix web run build
```

### Provider configuration

Discovery needs **one** model provider. Replay and the handoff demo need no key.
Copy [.env.example](.env.example) to a local `.env`, then fill in one group:

| Set `LLM_PROVIDER` to | Also set |
| --- | --- |
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `anthropic` | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| `gemma` | `GEMMA_BASE_URL`, `GEMMA_MODEL`, and `GEMMA_API_KEY` if required |

Process environment variables override `.env`. There is no automatic provider
fallback. Keep keys and private endpoints out of Git and recordings.
See [provider details](docs/providers.md) for errors and adapter limits.

## Run the product

```powershell
$env:CAPABILITY_RUNNER_BROWSER_HEADLESS = "false"
uv run capability-runner serve
```

Open **http://127.0.0.1:5000**. Keep this process running during your review.
Human takeover needs a local desktop and the managed Chromium window.

In **Discover**, choose **CoreBank Legacy · known profile** and enter:

```text
Open member 67890 and tell me how much is in their Savings account.
```

After successful Discovery, inspect the saved artifact. Choose **Replay with new
input**, enter `12345`, and expect **438221 minor units ($4,382.21), USD,
and zero Replay model calls**.

The [screenshot guide](docs/submission/test-product.md) continues through checking,
member-not-found, and physical handoff. If a tab was open during a rebuild,
hard-refresh it with **Ctrl+Shift+R**.

Interventions also offers **Start Sign-in Handoff**: use the public synthetic
credentials in the managed browser, then return control so Replay completes
the lookup. This is a demo sign-in gate, not production authentication.

## Run Discovery and Replay from the CLI

```powershell
uv run capability-runner demo through-line
```

This discovers the savings goal for member `67890`, saves the resulting
capability, closes Discovery, and replays that artifact in a fresh session for
`12345`. It checks the output and zero Builder/Replay model calls.
Configuration or verification failure produces a nonzero exit code.

Run these without a model key:

```powershell
uv run capability-runner demo exception
uv run capability-runner demo intervention
```

The first returns `BUSINESS_OUTCOME / MEMBER_NOT_FOUND`. The second tests approval
and same-session continuation through controlled HTTP actions. **The CLI handoff
is an automated test path; use the product for physical human takeover.**

Results go to `var/demo-runs/<run-id>/`: `summary.json`, `evidence.jsonl`, and,
for Discovery, the saved capability. Use `--output-root PATH` for another location.
See [command details](docs/submission/demo-entrypoints.md).

## Verify it

```powershell
uv run pytest -q
npm --prefix web test
uv run ruff check .
uv run pyright
npm --prefix web run typecheck
```

Ordinary tests exclude live-provider tests.
[Evaluation commands](evals/README.md) cover the 13-case banking suite.
[Progress](docs/progress.md) records completed checks; test counts alone are not
proof of product readiness.

## Current limits

Recorded evidence covers real-provider Discovery, artifacts, different-input
Replay, expected errors, and automated same-browser handoff tests.
**Physical human handoff acceptance remains outstanding**, including a reported
session with an unavailable browser preview.

The React UI and catalog exist. Account creation, desktop automation, voice,
screen sharing, Teach, and production multi-tenancy do not. The second app has
its own package; reuse of one identical artifact across tenants is not demonstrated.

This is a local, read-only review build. Sessions are lost on server restart.
The HTTP UI has no production login, and screenshots have no general PII redaction.
Use synthetic data. [Readiness](docs/submission/readiness-report.md) separates
evidence from remaining work.
