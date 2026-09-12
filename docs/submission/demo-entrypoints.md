# Demo Entrypoints

## Command contract

The installed `capability-runner` console script exposes three reviewer-facing commands. Each
command starts the synthetic CoreBank application on a free loopback port, runs real Chromium,
performs best-effort cleanup, and writes runtime output under `var/demo-runs/<run-id>/` by default.

| Command | Purpose | Provider requirement | Expected result |
| --- | --- | --- | --- |
| `capability-runner demo through-line` | Run genuine Discovery, compile and store the discovered capability, then load it for fresh deterministic Replay. | A valid provider configuration from `.env` or the process environment. No fallback is attempted. | Discovery `SUCCESS`; stored `lookup_savings_balance@1.0.0`; fresh Replay of member `12345` returns `438221` / `USD`; Builder and Replay make zero model calls. |
| `capability-runner demo intervention` | Run approval-blocked Replay, invoke the existing operator HTTP action on the same surface session, validate fresh state, and resume. | None. | `APPROVAL_REQUIRED`; operator Savings click; generation `0 -> 3`; resumed Replay `SUCCESS` with `98765` / `USD`; no earlier automation action repeats. |
| `capability-runner demo exception` | Replay the bundled capability for an unknown member without a model. | None. | `BUSINESS_OUTCOME` / `MEMBER_NOT_FOUND` with a safe summary and evidence log. |

Use `capability-runner --help` and `capability-runner demo --help` for command help. Each command
also accepts `--output-root PATH` for isolated acceptance runs.

## Prerequisites

- CPython 3.12 and `uv`.
- Locked dependencies installed with `uv sync --all-groups`.
- Playwright Chromium installed with `uv run playwright install chromium`.
- For `through-line` only, one valid provider configuration described by `.env.example` and
  `docs/providers.md`.

If live model configuration is absent or invalid, `through-line` exits before creating a run
directory and reports: `Live model configuration is required for discovery demo. See .env.example.`

## Runtime output

Every successful command creates:

- `var/demo-runs/<run-id>/summary.json`, the concise machine-readable result;
- `var/demo-runs/<run-id>/evidence.jsonl`, sanitized structured policy/action/outcome evidence.

The through-line additionally creates
`var/demo-runs/<run-id>/capabilities/lookup_savings_balance/1.0.0.json`. Paths stored in and printed
from the summary are portable relative paths. Runtime output under `var/` is ignored working data;
it is not the curated submission package required under `/evidence/` in P5.3.

On a terminal Discovery or Replay failure with an available browser session, the demo runtime asks
the Browser Surface Adapter for bounded failure evidence and records the sanitized surface details
as an `error` event. A known business outcome is instead recorded as an `outcome` event and is not
misrepresented as a technical failure.

Exit status is `0` only when the command reaches its expected result, `1` for runtime or
verification failure, `2` for missing/invalid live configuration, and `130` for cancellation.