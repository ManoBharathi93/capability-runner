# Capability Runner Design Report

## Architecture

I kept the runner in one Python process. The hard part is deciding who may act
on a live browser and when, so separate services would add coordination without
helping this demo. The CLI and React UI use the same backend. The frontend shows
state; it does not run workflows.

Discovery uses an LLM to connect a natural-language goal to the current interface.
The model proposes a small, typed action. The runner validates it and applies
policy before execution. It cannot accept arbitrary browser code from the model.
The loop has turn, action and time limits.

Replay intentionally has no model dependency. Once a procedure is saved, a model
would add new decisions, cost and uncertainty to each run. Replay follows the
artifact and checks current state. The [recorded through-line](evidence/through-line/summary.json)
used five Discovery model calls and zero Builder or Replay calls. Separate tests
load a generated package without provider configuration.

All automated actions pass through Action Gateway. It checks ownership, freshness
and policy before the browser adapter acts. During native handoff, the person
uses the retained browser directly; physical input is outside gateway enforcement.
One process keeps this boundary simple, but a restart loses active sessions.

## Artifact schema

I chose versioned JSON instead of a transcript or generated script. A reviewer
can inspect its inputs, outputs, ordered steps, conditions and allowed recovery
without reading a model conversation. Validation rejects unsupported versions
and inconsistent references before storage. The [saved example](evidence/through-line/capabilities/lookup_savings_balance/1.0.0.json)
contains a member input and balance/currency outputs, rather than one member's
recorded values.

A workflow names what a control means, such as opening Savings. A separate
application profile says how to find that control in a particular interface.
This separates business intent from labels, frames and page layout. A tenant's
markup may change while the procedure stays the same.

For an app without a prepared profile, the browser supplies temporary element
references. A deterministic compiler turns verified observations into durable
bindings. The model does not write selectors. A package contains the capability,
application profile and integrity metadata.

The cost is that the capability and profile must remain compatible. Generated
names can also be hard to read. A successful trace supports what was observed;
it cannot establish an unseen business outcome or prove another tenant works.

## Determinism & error handling

Replay checks inputs and application identity, resolves each target uniquely,
performs the saved action, and checks fresh state. The State Evaluator returns
true, false or unknown. Unknown never counts as success. The final result is
`SUCCESS`, a declared `BUSINESS_OUTCOME`, or `FAILURE` with a reason and context.

False success is more dangerous than conservative failure in banking. A plausible
balance from the wrong member may be repeated to a customer or used in a later
decision. A clear failure can be investigated. I therefore require matching
member identity, the requested account type and valid outputs before reporting
success. Merely reaching a page with a balance is insufficient.

Retries are narrow. A slow observation may be repeated within a declared limit.
An action with an uncertain effect is never automatically retried: the first
click may have worked even if its response was lost. Repeating a payment or
account-creation action could duplicate the effect. Those examples explain the
rule; this sandbox does not implement those banking operations.

The [not-found run](evidence/exception/summary.json) reports a business outcome,
and the [failure log](evidence/failure/evidence.jsonl) includes bounded state
evidence. The recorded 13-case evaluation covers expected successes and safe
failures, with zero false successes or Replay model calls. That is evidence for
these cases, not a reliability estimate for arbitrary websites.

## Heterogeneity & multi-tenant

The browser adapter owns Playwright objects. Engines use normalized observations
and semantic actions. A future desktop adapter could implement that contract with
OS accessibility or vision. No desktop adapter has been built.

CoreBank and LegacyBank B have both completed real-provider Discovery and fresh
Replay. Supported controls include ordinary visible HTML inputs, links, buttons
and result tables, with bounded same-origin frame support. Ambiguous, stale or
unsupported targets fail. The [browser scope](docs/submission/generic-browser-scope.md)
lists the limits.

Tenant reuse is a design goal: keep one workflow and supply narrow, reviewed
profiles for each app variant. Identity checks and unique target resolution must
still pass. The second banking app currently produces its own package. I have
not demonstrated one unchanged capability across two tenant profiles, so I do
not present this as cross-tenant reuse.

## Escalation & handoff

The implemented resumable path starts when Replay reaches an approval-required
action that is known not to have executed. The intervention includes the blocked
step, reason, session identity and safe context. Take control waits for admitted
automation to finish, then grants ownership of the same Chromium Page and
BrowserContext. The person clicks in that window; the product image is a preview.

The synthetic sign-in example uses the same approval boundary: a human signs in,
a fresh authenticated-state condition passes, then Replay completes the lookup.
Its credential-entry preview endpoint is disabled. It is not general session-expiry
recovery or production authentication.

Returning control triggers a fresh observation before automation resumes. The
person may have completed the blocked action, opened the wrong account, or closed
the page. Continuing from the old snapshot could repeat an action or return the
wrong result. The controller issues a new generation only after validation;
old requests cannot act with stale ownership.

[Automated handoff evidence](evidence/direct-browser/summary.json) records stable
browser identities, generation 0 to 3, no repeated earlier actions and zero
Replay model calls. Negative tests reject unchanged, wrong-account and closed
states. Headed Playwright input is an automated stand-in; physical human
acceptance remains outstanding. The owner's reported unavailable preview is
not a successful acceptance run.

Passive capture records bounded event kinds and opaque identities without field
values or keystrokes. It can miss events, so fresh state, rather than event count,
decides whether continuation is valid. OS focus is best effort.

## Safety

Authority comes from trusted configuration, not the goal, page text or model.
Allowlisted applications, routes and action types constrain automation. Unknown
actions are denied; configured risky actions require approval. The read-only
sandbox has a narrow allowance for its known search POST route.

Artifacts use parameter references. Evidence redacts configured sensitive keys,
secret wrappers and known runtime values before writing. Published screenshots
use reviewed synthetic data. Preview frames are transient.

These controls have limits. Physical human input bypasses gateway policy, and the
person must stop interacting after handback. The local HTTP UI has no production
authentication. Files are not encrypted, and redaction is not a general detector
of financial PII in text or screenshots. Action-authorization tests do not prove
user authentication or production data protection.

## Cuts

The React UI, catalog, live Discovery preview, package inspection, Replay and
evaluation commands are implemented. I left out account creation, desktop
automation, distributed scheduling, durable browser recovery, production login,
automatic profile repair, voice, screen sharing and Teach. They would add scope
without strengthening the demonstrated execution contract.

The public repository contains code, setup instructions and curated evidence.
The [progress record](docs/progress.md) links completed verification separately
from design intent. Evaluation currently supplies regression results, not a
persisted draft-to-approved capability gate.

My next step is to complete physical handoff acceptance. After that, I would
repeat model-free Replay against independent expected results, then test one
unchanged capability across two tenant profiles with deliberate drift. These
would strengthen the evidence for correctness and reuse before adding workflows.
