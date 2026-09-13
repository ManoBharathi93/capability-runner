# Product navigation repair

## Making the product paths usable

Interventions and Sessions expose the existing handoff. Savings and Checking are the chosen demo outcomes; no account-creation feature was added.

For current behavior, use [the product guide](../submission/test-product.md) and
[progress](../progress.md). The record below preserves the decision, tests and
limits at this subsystem's implementation date. Earlier phase restrictions and
operator-control descriptions are historical; the
[native handoff record](direct-browser-handoff.md) explains the later physical-input exception.

<details>
<summary>Implementation record: contracts, trade-offs and checks</summary>

## Scope and decision

The owner's 2026-09-13 request authorizes fixing inaccessible Interventions and Sessions
paths. The reported URL contains a repeated leading slash. The React router currently renders
Not Found for that path; the sidebar omits Interventions and the empty Sessions view offers no
navigation to start a handoff.

Normalize repeated slashes in the client pathname using an internal router location, preserving
query and fragment. Add Interventions navigation, a Sessions link to start a handoff, and a
manual refresh of backend-owned session state. After an operator action, request a fresh preview
so the visible session reflects the action. Session ownership and policy remain backend-owned.

An alternative is to document only the correctly spelled URL. That leaves the product's dead end
and missing navigation intact. The selected change is limited to presentation and routing; it
does not add a session registry or permit account creation. Sessions continue to list active
intervention sessions only, with that scope explicit in the page copy.

## Validation

Check repeated-slash navigation, sidebar access, empty-to-active session refresh, and historical
interventions in frontend tests. Rebuild the product and verify a real browser handoff through
Sessions and Interventions, including same-session continuation and zero Replay model calls.
Record completed results in `docs/progress.md`; this plan is not verification evidence.

The owner selected the existing sandbox scope: savings, checking, and approval/HITL.
Extend the generated-package integration tests with fixed independent savings/checking oracles,
stored Replay in a new workspace without provider configuration, and wrong-account-category
completion rejection in both directions. Extend the live UI checker to select checking explicitly.
No account creation or new banking business functionality is authorized by this repair.

</details>
