# Product UI behavior

The React/TypeScript UI is implemented. It displays backend-owned state and uses
the same execution core as the CLI. See [screenshots](submission/test-product.md)
and [current verification](progress.md).

## What each page does

| Page | User action | What the UI must show honestly |
| --- | --- | --- |
| Discover | Choose an app and enter a goal. | Current browser preview, progress, result and artifact. |
| Capabilities | Inspect saved definitions. | Inputs, outputs, steps and version; validation is not approval. |
| Runs / Evidence | Inspect execution records. | Actual outcomes and model/action counts, not sample metrics. |
| Interventions | Take the existing browser, act, then return. | Ownership, generation, blocked step and fresh validation result. |
| Sessions | Find active handoff sessions. | An empty list when none are active; not a global session registry. |
| Settings | Inspect local configuration status. | No false claim of production login or secret storage. |
| Teach | View the disabled shell. | Voice, screen sharing and teaching are not implemented. |

## Native handoff rules

Take control must request backend ownership. The embedded screenshot is a
non-interactive preview. The human acts in the same managed Chromium window,
outside gateway enforcement.

Return requests fresh state validation before automation resumes. Wrong, unchanged
or closed state cannot become success. Stop ends the attempt. Browser focus is
best effort; physical acceptance still needs a person to test it.

## Design and future work

Use navy, white and blue, clear status colors and readable spacing. Reference
images guide appearance only; names, metrics and success claims in mockups are
not runtime facts.

Any future teaching flow must use the existing artifact, policy and execution
boundaries. It needs explicit scope and data-handling review. A local deletion
promise cannot establish an external model provider's retention behavior.

The shared-backend direction is **ACCEPTED BASELINE**. Implemented UI and
completed tests are separate facts; [progress](progress.md) records
**VERIFIED BEHAVIOR**.
