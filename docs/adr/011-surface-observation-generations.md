# ADR-011: Fresh, bounded surface observations

**ACCEPTED BASELINE:** authorized surface observation hardening, 2026-09-14.
Implementation evidence is recorded separately in [progress](../progress.md).

## Constraint and decision

A model decision can arrive after the page has changed. An old element number
must never refer to a newly observed control. Keep the observation UUID for
session isolation and add a monotonic generation to each ref: `12:e4`.
Check generation and membership before resolving a locator. Keep mutation,
frame and original-node checks for changes between observation and action.
Compile durable bindings from observed facts; never persist runtime refs.
Observation generation versions page views. It does not replace the Session
Controller's separate ownership generation.

Use ARIA/native semantics first, supplemented by visible labels, forms, table
rows and named-frame context. Record actual source tags. Cap candidates, elements,
text, serialization and model context, marking truncation. A future visual
producer can use this normalized seam; no vision dependency is introduced.

After each meaningful action, await bounded load and DOM stability, then observe
again. Compare normalized state to produce small delta counts. Ignore ephemeral
IDs and recognizable clocks/UUIDs in the fingerprint. Two successive unchanged
observations stop generic Discovery. Current refs alone authorize target resolution;
the delta is explanatory. Policy and ownership still authorize execution.

## Alternatives and cost

Keeping only UUID checks already prevented several stale-node errors, but hid the
generation relationship from model decisions and evidence. Full DOM/accessibility
tree dumps would expose more data and cost more context. Pixel reasoning and bulk
actions add different failure modes outside this scope.

Conservative invalidation can require another observation or fail on a busy page.
Two quiet animation frames are not proof that delayed business work has finished.
The richer context increases measured character counts; it does not claim token
savings. Bounded text can omit needed evidence, which must remain non-success.
Fingerprint normalization is heuristic, not a general detector of irrelevant UI.

## Validation and revisit

Check stale/fabricated refs before lookup and dispatch; test session, iframe,
navigation and control changes; test duplicate/hidden/credential controls and
deterministic bounds. Verify search/results/account deltas, no-progress stopping,
injection denial, generated packages and model-free Replay. Keep a real-provider
run with safe metadata, plus separate stale injection tests. See the
[curated evidence](../../evidence/surface-observation/README.md).

Revisit observation sources when a required target cannot expose usable semantics,
or measured false stagnation justifies a narrower state comparison. Neither case
authorizes model decisions during Replay or relaxed action policy.
