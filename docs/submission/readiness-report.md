# Submission readiness

**The core is implemented and has evidence. Physical handoff acceptance remains
open.** I would not claim that the submission exceeds expectations while that
reviewer path is unresolved.

The assignment asks for one complete workflow covering every core requirement.
Savings lookup, account creation and checkout are alternative examples.
This submission covers savings, checking and approval/handoff; it does not
create accounts.

## What a reviewer can verify

| Area | Evidence | Limit |
| --- | --- | --- |
| Real model-driven Discovery | [Through-line summary](../../evidence/through-line/summary.json) | One recorded success does not establish provider reliability. |
| Saved artifact and fresh Replay | [Generated artifact](../../evidence/through-line/capabilities/lookup_savings_balance/1.0.0.json) and the same summary | Replay uses a different input and zero model calls. |
| Errors and false-success prevention | [Not-found result](../../evidence/exception/summary.json), [failure log](../../evidence/failure/evidence.jsonl), [evaluation](../../evals/README.md) | Safe failure counts as a passing negative test, not successful Discovery. |
| Second app and Checking | [Checking result](../../evidence/checking/ui-summary.json) | Its own package; not one unchanged artifact across tenants. |
| Human handoff | [Same-browser test evidence](../../evidence/direct-browser/summary.json) | Automated input passed; physical acceptance is pending. |
| Delivery and communication | Public source, [README](../../README.md), [REPORT](../../REPORT.md), [screenshot guide](test-product.md) | Clear writing cannot replace a working required flow. |

## Remaining acceptance check

The owner's earlier tab showed old controls. A fresh client loaded the new UI.
The session later reached human ownership, but its preview returned
`VIEW_UNAVAILABLE`. That is unresolved browser usability, not successful handoff.

Follow [the physical handoff steps](test-product.md#5-physically-take-over-the-existing-browser).
Record the run ID, same-session identity, action, result and generation.
Do not replace that proof with an automated browser click.

## Recorded checks

The latest full Python record has **380 tests passing**. The sign-in change passed
**38 focused Python tests and 12 frontend tests**.
Eight live-provider tests were excluded from ordinary pytest. Typecheck, build,
Ruff, Pyright and lock checks also passed. The banking evaluation passed 13 cases.

These are dated results in [progress](../progress.md), not tests rerun by opening
this page. The [manual checklist](manual-test-guide.md) gives reproducible checks.

## What would strengthen the submission

First finish physical handoff acceptance. Then deepen evidence for the existing
contract: repeated Replay with independent expected values, or one unchanged
artifact on two tenant profiles with a deliberate drift failure. These are next
work, not implemented qualification features.

Keep the cuts explicit: local sessions, read-only scope, provider variability,
no production authentication and no universal PII redaction. Desktop, voice,
Teach and distributed infrastructure remain out of scope. Extra business
workflows would not resolve those gaps.
