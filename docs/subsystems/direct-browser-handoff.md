# Subsystem: same-session direct browser handoff

## Status

- Design: **ACCEPTED BASELINE**, owner instruction of 2026-09-13.
- Implementation: implemented.
- Verification: automated checks passed; physical acceptance pending.

## Before implementation

The audit found that the product launched a headless browser, granted operator
ownership while starting the demo, and made Take Control scroll to semantic proxy
buttons. Return control already used the continuation coordinator's fresh state
validation. BrowserSurfaceAdapter retains the original Page and BrowserContext in
its session map until explicit cleanup; a native handoff can retain both.

The owner now explicitly authorizes a distinction from the previous gateway-only
operator rule: automated actions still require Action Gateway; physical human
actions in the existing managed window do not. OperatorActionGateway remains a
controlled test/CLI seam. Native interaction must never create an EXECUTED gateway
result. No new business functions, remote browser service, or teaching is needed.

Product start leaves the session pause_requested. Take control asks the existing
InterventionManager to grant ownership only after admitted actions quiesce, then
focuses the existing page. Reviewer mode is headed, configurable through
CAPABILITY_RUNNER_BROWSER_HEADLESS; CI may remain headless. Return control disables
passive capture, requests resume, and invokes the existing continuation validator.
Fresh validation is authoritative; capture is only supporting evidence. Closed,
unchanged, or wrong state must produce a structured non-success without reopening
the browser. Terminal product attempts release their process-local resources.

The adapter owns browser handles and bounded passive listeners. Capture stores
only event kinds, allowlisted element types, opaque page/frame/session identities,
and whether a value was omitted. It never reads values, text, URLs, keystrokes,
cookies, storage, or DOM snapshots. Input edits use change events, not key events.
Sensitive input controls are excluded. Native capture is best effort, including
across navigation; it cannot enforce policy on physical human actions or prevent
OS input after the operator says they have returned control.

Alternatives: retain proxy buttons (fails the requested semantics); add remote
co-browsing (adds infrastructure outside scope). Use the same desktop browser and
make the preview explicitly non-interactive. OS focus is best effort.

Boundary checks: direct Playwright Page interaction is an automated stand-in for
human input, never a claim of physical acceptance. Assert identity before/after,
generation 0 to 3, three initial automation actions without repeats, zero automated
Savings actions and zero model calls; unchanged/wrong/closed state cannot succeed.
Also verify stale dispatch and quiescence, capture provenance and omitted values,
frontend ownership rendering, and all required regression gates. Physical human
acceptance remains a separate manual gate.

## After implementation

ProductWorkflowService composes explicit take/focus/return/stop with the existing manager,
controller and continuation coordinator. BrowserSurfaceAdapter retains the handles and owns
bounded passive listeners. The frontend renders ownership and validated outputs, without
semantic-action proxy controls. Six direct-browser cases and the full 380-test Python suite
passed; frontend and headed UI evidence are recorded in [progress](../progress.md).
Physical human acceptance is not inferred from automated Page input.
