# CLI demo commands

Install with [README setup](../../README.md#setup). Run from the repository root.

| Command | Model key? | Expected result |
| --- | --- | --- |
| `uv run capability-runner demo through-line` | Yes | Discovery for 67890, saved artifact, fresh Replay for 12345: 438221/USD. Builder and Replay call no model. |
| `uv run capability-runner demo exception` | No | `BUSINESS_OUTCOME / MEMBER_NOT_FOUND`, with no balance. |
| `uv run capability-runner demo intervention` | No | Approval, same-session controlled HTTP action, validated continuation: 98765/USD, generation 3. |

**The CLI intervention is automated.** Use the
[product handoff](test-product.md#5-physically-take-over-the-existing-browser)
to test a person's interaction with the retained browser.

## Where to look afterward

Each run writes to `var/demo-runs/<run-id>/`:

- `summary.json`: result and counts.
- `evidence.jsonl`: safe event log.
- `capabilities/lookup_savings_balance/1.0.0.json`: the through-line's saved artifact.

Use `--output-root PATH` for another directory. Local `var/` is ignored by Git.
Only reviewed files belong in the public [evidence folder](../../evidence/README.md).

A failed run may include bounded visible-state text when the browser is available.
A known business outcome is recorded separately from a technical failure.

## Exit codes and help

| Code | Meaning |
| --- | --- |
| 0 | The command reached its expected result, including an expected not-found outcome. |
| 1 | Execution or result verification failed. |
| 2 | Live provider configuration is missing or invalid. |
| 130 | Cancelled. |

```powershell
uv run capability-runner --help
uv run capability-runner demo --help
```

The commands start their own local synthetic target and Chromium. They do not
require the product server to be running.
