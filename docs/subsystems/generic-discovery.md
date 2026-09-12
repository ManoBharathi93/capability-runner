# Generic Discovery, live workspace, and evaluation

Design: **ACCEPTED BASELINE**. Implementation: implemented. Verification: passed.
Completed behavior and its evidence are recorded in [progress](../progress.md) as
**VERIFIED BEHAVIOR**, including both real-provider UI acceptances and fresh zero-model Replay.
Authorization: the owner's 2026-09-12 GENERIC DISCOVERY + LIVE WORKSPACE + EVALUATION request.
This authorization supersedes the historical P1.0/current-stop text for this milestone only.
Teach, desktop automation, and external publication remain outside this work.

## Audit before implementation

The source search covered `src/`, `demo_app/`, `web/src/`, and `tests/` for CoreBank,
lookup_savings_balance, member.search/results/accounts, savings, fixed goals, and required
completion targets. Categories: A demo composition, B fixtures/tests, C generic abstraction,
D production genericity violation.

| Occurrences / owning file | Category | Finding / disposition |
| --- | --- | --- |
| `application/demo_configuration.py`: all banking names, bindings, policies, output templates | A | Explicit trusted demo composition; never imported by generic engines/compiler. Preserve known-profile path. |
| `demo_app/app.py`, fixtures, templates, CLI through-line/intervention, reviewer runtime | A | Actual banking app and explicit demo. Preserve. Fixed goal only belongs in explicit demo commands. |
| `tests/` and `web/src/App.test.tsx`: all banking strings | B | Test data and assertions; preserve relevant regression coverage. |
| `contracts/requests.py`, Discovery engine/presenter: required_completion_targets | C | Optional trusted-profile completion constraint; preserve, add separate grounded profile-less mode. |
| `surfaces/browser_surface_adapter.py`: four fixed English outcome classifiers | D | Move classification configuration to trusted profile data; browser mechanics cannot recognize banking prose. |
| `demo_app/product_http.py`: exact equality gate and discarded submitted goal | D | Validate nonempty bounded goal; forward actual text; return asynchronous run/session identity. |
| `web/src/pages/DiscoverPage.tsx`: exact equality gate, fixed goal and single-task copy | D | Arbitrary English, application choice, live same-session workspace and artifacts. |
| `web/src/pages/RunsPage.tsx`, product HTTP replay: fixed artifact/input routing | D | Add generated package replay using declared typed inputs; retain explicit demo compatibility. |
| Intervention UI label and demo-specific intervention composition | A | Explicit banking intervention demonstration, not generic Discovery behavior. |

Before: four browser classification branches and three product restrictions (HTTP goal,
frontend goal, fixed Replay routing). DiscoveryEngine and CapabilityBuilder have zero app-specific
branches, but only support predeclared semantic targets. The full search inventory is retained
locally during implementation; this table classifies every matching owner/path family.

## Contracts, state, and implementation choices

Add bounded typed browser observations and strict inspect/fill/click/complete/fail decisions.
BrowserSurfaceAdapter owns ephemeral references, document mutation revisions, browser handles,
visibility, safe text, locator construction and uniqueness checks. No model-authored executable
field is accepted. References expire on a new observation and on DOM mutation/navigation.
Discovery owns the model loop; all actions still traverse ActionGateway and SessionController.
PolicyGuard authorizes only an independently configured read-only sandbox origin/route scope;
the goal, page content, and generated profile confer no authority. Unknown effects are denied.

The deterministic binding compiler derives semantic IDs and resolution data from adapter-verified
properties, then reuses CapabilityBuilder/Validator. Capability and profile remain separate files
in an immutable logical package. Runtime values stay out of both. Replay uses the existing engine,
verifies application identity before actions, and never constructs a ModelClient.

The product keeps process-local active runs, bounded transient PNG views, safe event polling,
and typed replay forms. Completed packages remain in local artifact storage. The existing visual
system and operator handoff are reused.

Alternatives: model-generated browser code was rejected because it violates data-only execution;
manual second-app profiles cannot establish profile-less discovery; an unrestricted browser would
violate the approved safety boundary. No significant dependency or service is needed. Evaluation
suite files use JSON (also valid YAML) to avoid introducing a YAML dependency.

Costs: bounded snapshots may omit relevant controls; inaccessible controls, ambiguous bindings,
unverifiable entity identity, dynamic labels and unsupported output semantics must fail closed.
A successful trace cannot establish unobserved business outcomes. Known-profile business outcomes
remain available; generic packages only claim observed/validated facts.

## Falsifying checks

First check: observe a genuinely unprofiled page, reject a ref after DOM mutation, and uniquely
re-resolve a compiler-produced binding. Then discover and replay a differently structured banking
app with a scripted client; repeat explicitly with the configured real provider. Test wrong entity,
prompt injection/policy denial, hidden/duplicate controls, app mismatch, bounded failures, artifact
separation, same-session view, arbitrary goal submission, and zero Replay model calls.
Record actual commands/results in `docs/progress.md`; acceptance requires both live cases.

## Completed boundary and remaining limits

The four browser banking-text classifiers moved to trusted profile data. Exact frontend/backend
goal gates and fixed-only Replay routing were removed. Generic Discovery, observation and binding
compilation have zero banking-specific branches; explicit demo composition remains separate.
Both live cases and the final gates passed. The ordinary suite has 371 passing tests, with eight
live tests excluded. Normal Discovery and Replay evaluation commands each passed 13 cases.

This supports bounded read-only browser extraction, not every possible meaning of arbitrary
English. Input recognition currently supports numeric/alphanumeric identifiers and quoted spans;
completion needs visible identity and supported output parsers. Generated packages do not infer
unobserved business outcomes. Unsupported UI primitives, drift and ambiguity stop safely.
Provider timeout/errors remain possible and are recorded as non-success. One Discovery runs at a
time, with at most eight retained process-local sessions until server shutdown. Preview images do
not provide universal PII redaction. Teach and external publication have not started.
