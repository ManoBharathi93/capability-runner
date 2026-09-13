# Visual Fidelity Report

This compares an earlier UI build with its visual references. It is an appearance check, not proof of workflow correctness or physical human handoff.

See [the screenshot guide](../submission/test-product.md) and
[progress](../progress.md) for the reviewer path and current evidence.

<details>
<summary>Detailed visual record</summary>

## Scope and method

The four files under `docs/references/ui/current/` are the complete P5.4b visual reference set.
Each implemented route was captured from the running React client and real local product API at the
reference viewport of `1448 x 1086`. The resulting PNGs are under
`docs/references/ui/implemented/`.

Comparison is structural and semantic rather than pixel-identical because reference values are
illustrative while implementation values must come from validated local artifacts and current
runtime state. `PASS` means the defining composition and visual language are preserved. `PARTIAL`
means an intentional runtime-truth difference remains. There are no major `FAIL` results.

## Results

| Reference | Implemented capture | Result | Evidence and intentional differences |
| --- | --- | --- | --- |
| `home.png` | `implemented/home.png` | PASS | Preserves the 226px navy rail, 70px header, greeting band, three workflow actions, four metrics, recent-runs table, right status rail, spacing, typography hierarchy, and status color vocabulary. Counts, runs, environment, and health text are backend-derived or explicitly unavailable rather than copied from the reference. |
| `capability-library.png` | `implemented/capability-library.png` | PASS | Preserves the dense library/detail split, selected-row treatment, filters/search geometry, primary run action, schemas, dividers, chips, and right-rail proportions. The single listed capability, version, schemas, steps, and known outcome come from a validated `CapabilityDefinition`; unsupported authoring/history actions are visually unavailable. |
| `run-detail.png` | `implemented/run-detail.png` | PARTIAL | Preserves the Home-selected shell, breadcrumb/title/status hierarchy, horizontal progress strip, large evidence surface, right activity timeline, and blue/green status language. The reference depicts an active run with a live preview; the capture uses a successful persisted through-line and therefore shows sanitized evidence with no fabricated browser view. This is a deliberate privacy and lifecycle correction. |
| `human-intervention.png` | `implemented/human-intervention.png` | PASS | Preserves the paused badge, lavender intervention banner, live-browser/details split, safety notice, semantic action area, and return/stop actions. The browser image is the current bounded `SurfaceView`, and reason, ownership, blocked action, controls, and replay state come from the existing same-session intervention path. The reference's illustrative login screen is not reproduced. |

## Responsive and state checks

- All four implemented PNG headers report exactly `1448 x 1086`.
- The capture harness loaded `/`, `/discover`, `/capabilities`, `/runs`, and `/interventions` at
  `390 x 844` and asserted that document width did not exceed viewport width.
- CSS animation and transition effects are disabled only in the capture browser so screenshots
  represent settled states without changing product motion.
- The intervention capture starts a real managed handoff, waits for the live surface image, captures
  the active state, and stops the session in a `finally` cleanup path.
- The run-detail capture prefers a genuine successful `through-line-*` record and falls back to the
  newest real run only when no such record exists.

## Truth and privacy review

No capture contains provider credentials, private endpoints, raw model messages, selectors, DOM,
or a replay input value. Historical sessions do not claim to have live browser imagery. Teach
remains a visual-only P5.4b route with media controls disabled; no P6 behavior is represented.

## Generic Discovery workspace acceptance

The current Home reference remains the design anchor: navy sidebar, pale blue page, Manrope,
white bordered panels, blue primary actions and green success feedback. The new Discover split
uses a goal/lifecycle column and a larger same-session legacy application. Both generated artifact
types are inspectable separately, with typed Replay immediately below.

Actual captures are in `docs/references/ui/implemented/generic-discovery/`:

- `corebank-known-live.png`, `corebank-known-complete.png`, `corebank-known-replay.png`;
- `bank-b-live.png`, `bank-b-complete.png`, `bank-b-replay.png`;
- `business-outcome.png`, `handoff-active.png`, `handoff-completed.png`.

Visual inspection: PASS for the workspace hierarchy and established design language. The UI
walkthrough observed eight distinct CoreBank frames and nine LegacyBank-B frames, each from one
managed session; these are actual changing browser views. Both UI Replay results were 438221/USD
with zero model calls. The handoff completed after fresh validation with generation 0 to 3.
Five routes again passed the 390 x 844 no-horizontal-overflow check. Full-page Replay captures
show the sticky shell at the current scroll offset; this is a capture artifact, not a fabricated
page state. New captures intentionally include only synthetic demo identifiers. Provider failures
and passing run IDs are recorded in `docs/progress.md`.

</details>
