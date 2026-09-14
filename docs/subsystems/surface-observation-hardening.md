# Surface observation hardening

**ACCEPTED BASELINE:** owner authorization of 2026-09-14 covers versioned runtime
refs, bounded perception, normalized changes, adversarial tests and live acceptance.
It does not authorize new business workflows, vision execution, bulk actions or
changes to Replay authority. Completed verification is recorded in [progress](../progress.md)
and the [curated acceptance](../../evidence/surface-observation/README.md).

## Audit before editing

1. Each observation has a UUID, but no explicit generation integer.
2. `eN` refs are session counters associated with that UUID and original nodes.
3. Refresh clears refs; mutation observers and node identity reject old DOM refs.
4. Extraction combines DOM-derived roles, ARIA labels, HTML labels and row context.
5. The presenter sends selected fields, never full HTML or locator definitions.
6. Bounds exist: 64 elements, 8 headings, 200 nearby characters, 256 element-text
   characters, 600 candidate nodes per frame, and 16,000 presented characters.
   Truncation is not fully described, headings/history are not uniformly masked,
   and there is no bound on the complete internal serialized observation.
7. Generic Discovery observes on each turn; the adapter awaits navigation/load
   through existing bounded Playwright waits. No bulk action API exists.
8. Known-profile Discovery compares snapshots; generic Discovery only compares
   consecutive action proposals. Neither generic normalized deltas nor a stable
   observation fingerprint excluding ephemeral IDs are provided.
9. Existing generic surface/package/safety tests cover stale UUID/DOM refs,
   ambiguity, prompt injection, input masking and model-free fresh Replay.
10. Keep those checks. Add generation-prefixed refs, early unknown/stale errors,
    bounded source/context metadata, deterministic normalized fingerprints/deltas,
    and no-progress integration. Reuse existing binding compilation and gateway.

## Decision and validation

Every successfully collected normalized observation owns a new session-monotonic
generation. The UUID remains a cross-session/page discriminator. Mutations and
frame changes invalidate refs immediately; a new generation is issued on the next
observe cycle. Stale generations fail before locator lookup; unknown current refs
and never-issued future generations fail separately. Local IDs can repeat without
making old refs usable. Generation advances even if collecting the replacement
fails, so a failed refresh cannot restore old references.

Accessibility attributes and native form semantics contribute first, supplemented
by bounded visible DOM context. Source tags report actual provenance; they are a
seam for a future producer, not evidence of a visual model or full accessibility
tree. Caps apply before presenting data and before serializing internal snapshots.
Safe aggregate delta counts compare normalized state, not observation IDs or node
handles. Current observations alone authorize references; deltas are explanatory.

The alternative is pixel-driven or full-DOM reasoning, which adds cost and data
exposure outside scope. Conservative invalidation can cause extra observations.
No-change termination remains bounded and cannot turn uncertainty into success.
Evidence stores counts and fingerprints, never raw observations. Validate stale,
fabricated, changed-frame, navigation, duplicate, oversized, hidden, injection,
credential and no-progress cases, then full regression and a live Discovery/Replay.

## Completed evidence

**VERIFIED BEHAVIOR:** the recorded real-provider run used five current-generation
decisions and four actions, built a package without ephemeral refs, and returned
438221/USD on fresh Replay for a different input with no model calls. Focused
tests reject stale, fabricated and changed-frame refs before locator lookup or
dispatch. Search, results, details and account transitions change the normalized
state; unchanged pages terminate. Full regression passed 402 cases with eight live
cases excluded. See progress for exact checks and the initial harness mismatch.

Busy pages can fail the bounded DOM-stability check. Quiet frames do not prove
delayed business work is complete. Text caps and imperfect accessibility may omit
needed evidence. Clock/UUID normalization is deliberately narrow. This work adds
no production auth, universal PII redaction, vision, cross-tenant reuse or physical
handoff acceptance.
