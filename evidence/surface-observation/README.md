# Surface observation acceptance

The [summary](summary.json) records a real Gemma run on 2026-09-14 against the
synthetic CoreBank app, without a prepared target profile. The goal was:

> For member 67890, find their Savings account and read the current balance.

Five model calls used generations 2 through 6. Every decision cited only current
refs and the matching observation UUID. Fill, search, member opening and Savings
opening each produced a fresh view with a meaningful change. Generation 1 was
the workspace's initial inspection before the model loop.

The [saved capability](package/capability.json), [profile](package/application-profile.json)
and [metadata](package/metadata.json) were copied unchanged. Fresh Replay used
member `12345` and returned **438221 minor units, USD**, matching the independent
fixture expectation. It executed four saved steps and made zero model calls.
The [Discovery log](discovery.jsonl) and [Replay log](replay.jsonl) are unchanged
copies; they contain safe generation/count/fingerprint metadata, not page dumps.

The [initial acceptance](initial-acceptance.json) is also retained. That run
completed Discovery and Replay, but the first script expected only balance and
currency and rejected an additional `account_type` output. The script now checks
that optional output against the independent value `Savings`, and still rejects
unexpected fields. The final run above passed. Model response variation remains
a limitation; this is not a reliability estimate.

## Size measurements

[Before](size-before.json) and [after](size-after.json) use the same three fixture
pages and goal, without model calls or action history. These are characters and
UTF-8 bytes, **not token estimates**. Additional generation, source and change
metadata increases context size. It remains bounded.

| Page | Normalized characters, before → after | Model characters/bytes, before → after | Controls | Element text + nearby characters |
| --- | --- | --- | --- | --- |
| Search | 4109 → 4883 | 1255 → 2014 | 5 | 53 |
| Member details | 9852 → 11412 | 2590 → 4278 | 6 | 202 |
| Savings | 5700 → 6814 | 1733 → 2889 | 4 | 105 |

The live summary has different sizes because it includes action history and a
different goal. Caps are 64 elements, eight headings, four frames, 8,192 visible
text characters, 65,536 serialized snapshot bytes and 16,000 model-context
characters. Text limits can omit needed evidence; omission must not become success.

## Reproduce the checks

From the repository root, after normal setup:

```powershell
uv run pytest tests/integration/surfaces/test_observation_hardening.py tests/integration/surfaces/test_observation_discovery.py tests/unit/discovery/test_generic_safety.py -q
uv run python scripts/measure_surface_observations.py var/observation-size.json
uv run python scripts/verify_surface_observations.py --live --output-root var/observation-review
```

Only the last command uses the configured provider. It starts its own local
synthetic target, builds a new package and replays it. The recorded package's
loopback port belonged to this acceptance run; it is not a hosted application.

The stale-reference tests inject old and invented refs separately and assert no
locator lookup or dispatch. Their unchanged [stale-ref](stale_element_ref.jsonl),
[unknown-ref](unknown_element_ref.jsonl) and [no-progress](no_progress.jsonl) logs
each show one initial permitted action and no second action. They do not alter
live logs. Read `metadata.result_reason_code` in their final event:
`DISCOVERY_COMPLETED` means the loop ended, not that the goal succeeded. Browser tests also
cover frame/navigation invalidation, hidden/duplicate controls, ARIA/HTML/DOM
sources, deterministic truncation and workflow changes. Model/context tests check
masking and no-progress stopping. Existing injection and wrong-outcome tests
retain false-success protection. Full check results are in [progress](../../docs/progress.md).

This acceptance does not establish physical handoff, cross-tenant reuse, vision,
production authentication or general PII redaction.
