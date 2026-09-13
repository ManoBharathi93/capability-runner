# Screenshot provenance

All images are actual Chromium captures of the synthetic demo. No generated imagery,
retouched balances, or mocked API responses were used. The guide captures were taken
on 2026-09-13. Input fields are cleared by the product after Replay; the preview
continues to show the original Discovery session, while the result belongs to Replay.

| Files | Execution and verification |
| --- | --- |
| `savings-discovery.png`, `savings-replay.png`, `member-not-found.png` | Real-provider Discovery `discovery-9e44b3db5f4d489591ca4e0460958c28`; five model calls; six changing frames. Fresh Replay `replay-d548d1e77f974c0c99ea0bfb709b5b54` returned 438221/USD, then the unknown-member Replay returned MEMBER_NOT_FOUND. See [script result](savings-ui-check.json). |
| `checking-replay.png` | Real-provider Discovery `discovery-fdd34a0aeb494281abf1813700b73855`; four model calls; four changing frames. Fresh Replay `replay-526f15f18daa4ac7a1b68a25ab3d5c16` returned 15840/USD. See [script result](checking-ui-check.json). |
| `handoff-paused.png`, `handoff-human.png`, `handoff-completed.png`, `sessions-human.png`, `managed-browser-before.png`, `managed-browser-after.png` | The [direct-browser UI check](../../../evidence/direct-browser/ui-check.json) identifies the isolated headed run and stable browser identities. Playwright directly operated the retained Page as an automated stand-in. Physical human acceptance is not claimed. |

Reproduce the Discovery captures with `scripts/verify_discovery_workspace.py`, using
`--application corebank-known` or `--application bank-b --product checking`, one at
a time. Reproduce native handoff with `scripts/verify_workspace_handoff.py --headed`.
The scripts initially write to their documented working directories; these selected
images and JSON results were copied unchanged after inspection. Checks and failed
attempts are recorded separately in [progress](../../progress.md).

The bank fixture IDs, names and balances are public synthetic data. Screenshots are
not evidence of universal PII redaction or safe capture of real customer accounts.
