# Progress

## Current evidence summary

This is a dated record of completed work. It is not a claim that every run succeeds.

| Check | Latest recorded result |
| --- | --- |
| Ordinary Python regression | 380 passed; eight opt-in live cases excluded. |
| Frontend | 11 tests passed; typecheck and production build passed. |
| Static checks | Ruff, Pyright and lock consistency passed. |
| Banking evaluation | 13 cases passed, including expected safe failures; zero Replay model calls. |
| Real-provider product runs | Savings and Checking completed, then replayed with different inputs. |
| Native browser handoff | Automated same-Page/context tests passed. Physical acceptance remains pending. |

Evidence: [through-line](../evidence/through-line/summary.json),
[Checking](../evidence/checking/ui-summary.json),
[direct-browser handoff](../evidence/direct-browser/summary.json).
The recorded unavailable preview in the owner's session remains unresolved.

## Documentation readability pass — 2026-09-13

The owner requested shorter public writing and an uncommitted deep learning
guide. Public entry pages now use plain explanations, smaller tables and links
to evidence. Historical records stay available below instead of being required
reading. Stale frontend, handoff and test-count claims in current guides were
corrected. No runtime code or evidence JSON was changed by this pass.

Completed documentation checks are **VERIFIED BEHAVIOR**: 224 local links and
section anchors across public Markdown and the private guide resolve; no public
page links to the private guide. REPORT has exactly the seven required headings
and 1,185 words. The private guide is ignored and untracked. Added public text
contains no configured secret/private endpoint or local user path. Git scope
and whitespace checks passed. Local results are in
`var/readable-docs-validation.json`. The earlier runtime suites were not rerun
for prose changes.

## Reading the history

**ACCEPTED BASELINE** is a decision. **PROPOSED IMPLEMENTATION DETAIL** is an
unresolved choice. **VERIFIED BEHAVIOR** requires completed evidence.
Older phase labels, test counts and operator-control descriptions are dated
records; later entries explain changes.

<details>
<summary>Dated engineering history and exact verification commands</summary>

## Reviewer UI diagnosis and private narration — 2026-09-13

The owner reported the old intervention controls after the native handoff update.
Read-only inspection found that the running server delivers the current hashed
frontend bundle, while the screenshot contains superseded labels. The active
intervention remains pause_requested, generation 1. A fresh Playwright client
opened that same intervention and verified Managed browser preview, enabled Take
control, disabled Return control to automation, and no old Return Control to Agent
button. No mutating requests were issued. These are **VERIFIED BEHAVIOR**, recorded
locally in `var/current-client-check.json` and `var/current-client.png`.
This supports an already-open stale client as the cause; no server restart or
session replacement was needed. Physical takeover acceptance is still pending.

A subsequent read showed operator_controlled, generation 2, but the preview
returned VIEW_UNAVAILABLE and evidence recorded HUMAN_CAPTURE_UNAVAILABLE.
The original managed browser's usability has therefore not been established;
loading the new controls is not a handoff acceptance pass. The owner received
instructions to stop the unusable attempt and start a fresh handoff if its window
is gone. No automated input was substituted for the owner's physical check.

The live catalog also contains the verified checking package, displayed under its
generic generated name. The screenshot guide now explains that naming limit and
how to reload the updated interface. Account creation remains outside the owner's
explicitly selected scope. The readiness report replaces unconditional READY with
the current evidence and the outstanding physical handoff check.

At the owner's request, personal recording narration is retained locally but removed
from the tracked submission, with its exact path ignored and public links removed.
This changes the current branch tree; it does not rewrite previously published commits.
No runtime implementation changes are part of this documentation correction.
Validation: 49 local links across README, REPORT and the three reviewer guides
resolve; REPORT retains exactly seven required headings. The private narration
still exists locally and is ignored. Changed documentation passes the local-path
scan and Git whitespace check. The earlier regression suites were not rerun for
these documentation-only edits.

## Direct native-browser handoff and screenshot guide — 2026-09-13

The owner's attached instruction explicitly authorizes physical human control of the existing
headed browser. This supersedes the former gateway-only rule **for physical human input only**.
Automated actions still pass through Action Gateway. The audit and trade-offs are in
[direct-browser-handoff.md](subsystems/direct-browser-handoff.md), **ACCEPTED BASELINE**.
No account-creation functionality, voice, Teach, remote co-browsing, or authentication was added.

Implementation: product start pauses before Savings. Take control delegates ownership and
quiescence to the existing manager/controller; Focus brings the existing Page forward. The
preview is non-interactive. Return disables passive capture, enters resume_requested, and
runs fresh validation before restoring automation with a new generation. Failed validation
and browser closure terminate the attempt without replacement or success outputs.
Sessions displays active handoff identities and ownership. The CLI operator gateway remains
an explicitly separate controlled test seam.
HTTP transitions recheck active membership after obtaining the per-intervention lock, so a
queued duplicate cannot use a runner that an earlier request has already closed.

Completed results are **VERIFIED BEHAVIOR**:

| Check | Completed result | Evidence |
| --- | --- | --- |
| Full regression | `uv run pytest -q --junitxml=var/direct-browser-full-tests.xml`: 380 passed, 8 live deselected, 388.61 seconds on final rerun. | Captured output and local JUnit; includes six cases in `tests/end_to_end/test_direct_browser_handoff.py` |
| Direct browser boundary | Same Page/BrowserContext/surface; generations 0→1→2→3; automatic fill/search/member-open each once; automatic Savings zero; operator gateway zero; fixed oracle 98765/USD. All three provider adapters patched to fail on any model invocation; zero invocations observed. | Direct-browser test module |
| Negative and privacy checks | Unchanged page, wrong account, closed page and stale automation rejected. Missing capture still allows a valid fresh result. Completed edit and selection record redacted indicators; password/OTP controls excluded. Existing quiescence, duplicate continuation and ownership tests also passed. | Direct-browser tests; full controller/manager/continuation suites |
| Concurrent HTTP handback | Two callers obtained the same active intervention before a held transition lock was released. Exactly one returned SUCCESS and the queued duplicate returned INTERVENTION_NOT_ACTIVE; the three initial browser actions still each occurred once. | Controlled real-browser experiment; `var/duplicate-handoff-check.json` |
| Headed product UI | `uv run python scripts/verify_workspace_handoff.py --headed`: same identities, successful model-free continuation, no repeats, Sessions navigation/removal and six mobile routes passed. | [Curated native handoff](../evidence/direct-browser/ui-check.json) |
| Frontend | 11 tests passed; TypeScript and Vite build passed. Covers actual ownership controls, no Savings proxy button, and success/failure rendering. | `web/src/App.test.tsx`, `web/src/pages/InterventionsPage.test.tsx`; captured commands |
| Static checks | Ruff passed; Pyright zero errors/warnings; `uv lock --check` passed, 31 packages resolved. | Captured commands |
| Documentation/privacy | 63 local Markdown links resolve; no configured credential/private endpoint found in changed text. REPORT retains exactly the seven required headings and 1,829 words. Ten published PNGs were inspected as synthetic UI captures. | Final link/credential scan; screenshot provenance |
| Fresh real-provider savings | Five Discovery calls, six changing frames, different-input Replay 438221/USD and MEMBER_NOT_FOUND, zero Replay calls. | [Screenshot run record](submission/screenshots/savings-ui-check.json) |
| Fresh real-provider checking | Four Discovery calls, four changing frames, different-input Replay 15840/USD, zero Replay calls. | [Screenshot run record](submission/screenshots/checking-ui-check.json) |

The first privacy check used Playwright select_option, whose programmatic change did not pass
the trusted-input filter. Native ArrowDown selection verified the intended physical-input behavior;
the final full suite passed. One concurrent checking submission was rejected before a run ID
was issued (HTTP 422 / DISCOVERY_NOT_STARTED). A separate subsequent checking submission
completed; the rejected attempt is not counted as a successful Discovery.

The [README-linked screenshot guide](submission/test-product.md) maps assignment scenarios
to inputs, expected outputs, actual images and harness-only edge cases.
Historical operator-HTTP records below remain historical.

Physical acceptance: **MANUAL_ACCEPTANCE_REQUIRED**. Headed Playwright input is an automated
stand-in. The local product was refreshed and the owner received the physical acceptance steps;
no physical response has been recorded here. OS focus is best effort; physical input is outside
gateway policy and cannot be OS-locked after handback. Capture is bounded, best effort and not
a tamper-proof audit channel. Active ownership remains process-local. Voice and Teach are not
implemented.

## Product navigation and banking depth repair — 2026-09-13

The owner authorized repairing Interventions/Sessions and explicitly selected existing-sandbox
verification: savings, checking, and approval/HITL. No account-creation business functionality
was added. The decision and boundary tests are in
[product-navigation-repair.md](subsystems/product-navigation-repair.md).

Implementation: Interventions now appears in the sidebar; repeated pathname slashes normalize
internally while preserving query and fragment. Sessions provides an entry point and manual
refresh, and explicitly lists active handoff sessions rather than all Discovery sessions.
Operator actions refresh the preview. Discover documents supported goals and fixture IDs.

Completed checks are **VERIFIED BEHAVIOR**:

| Check | Result | Evidence |
| --- | --- | --- |
| Frontend regression and build | 9 tests passed; TypeScript and production build passed. Covers repeated-slash routing, active navigation, Sessions empty/active refresh, and historical handoffs. | `web/src/App.test.tsx`; captured test/build output |
| Real product handoff | Same-session SUCCESS, generation 0 to 3, 98765/USD, zero Replay calls, no repeated side effect. Sessions links and removal on completion, preview refresh, and six mobile routes passed. | `var/manual-handoff.json`; run `intervention-e860b24772a34d6ab89c582362693dde` |
| Real-provider checking UI | SUCCESS, 4 model calls, 3 actions, one managed session with 3 changing frames; different-input fresh Replay 15840/USD, zero Replay calls. | `evidence/checking/`; run `discovery-4c91d558045148f7b1ab20b8d09d0ed5` |
| Real-provider savings UI | SUCCESS and different-input fresh Replay 438221/USD with zero calls; unknown input returned MEMBER_NOT_FOUND. Six changing frames in one managed session. | `var/manual-corebank-known.json`; run `discovery-805a113f0c314a78b74a196575ad05e2` |
| Focused Python regression | 18 passed in 155.75s. Independent fixed savings/checking oracles; saved package replayed through a new workspace with empty provider configuration; wrong member, wrong account in both directions, injection, restricted/expired/slow outcomes, and product API checks. | `var/navigation-depth-tests.xml`; package, browser Replay, and product HTTP test modules |
| Static checks | Ruff passed and Pyright reported zero errors/warnings. | Captured command output |
| Current collection | 374 ordinary cases selected, 8 live excluded; 382 total. The full suite was not rerun; the prior full Python baseline remains 371 passed. | `pytest --collect-only -q` |

One additional savings submission was rejected before Discovery because the long-running product
had retained eight finished workspaces. Read-only status inspection confirmed eight retained and
zero running Discovery sessions; no active handoff existed. Restarting the idle product freed
the process-local sessions, after which the savings UI check above passed. Stored packages and
evidence were preserved. The UI checker now records an HTTP rejection explicitly instead of
raising an unexplained missing-run-ID error. The eight-workspace limit remains implemented and
is documented in the manual guide.

The four new checking evidence files were copied unchanged from actual runtime output and passed
JSON/JSONL parsing and credential, private-path, and invocation-ID scans. Their generated binding
remains in the local package; the curated capability is an inspection artifact. Older evidence
and provider failures have not been relabeled as new passes.

## Current phase

**GENERIC DISCOVERY + LIVE WORKSPACE + EVALUATION: PASS.** The owner's 2026-09-12
request authorizes the bounded profile-less browser path, generated application bindings, live
Discovery workspace and evaluation harness. This supersedes the older P1.0/P5 stop text for this
milestone. Implementation is complete and scoped acceptance is **VERIFIED BEHAVIOR**: both live
applications, real product UI, safety regressions and final gates passed as recorded below.
Teach/P6 remains outside scope. The source was published to the public Capability Runner GitHub
repository on 2026-09-12, and anonymous repository and raw README access returned HTTP 200. The
mandatory submission matrix is now 30 PASS, 0 PARTIAL, 0 MISSING.

Status terms are intentionally independent:

- Design status: **ACCEPTED BASELINE** or **PROPOSED IMPLEMENTATION DETAIL**.
- Implementation status: `not started`, `in progress`, `implemented`, or `blocked`.
- Verification status: `not run`, `passed`, `failed`, or `inconclusive`.

## Design acceptance

| Decision | Design status | Canonical record |
| --- | --- | --- |
| Modular monolith; Python/Pydantic core; React/TypeScript product frontend; command and thin web interfaces share the core | ACCEPTED BASELINE | ADR-001 |
| Discovery with provider-neutral Model Client separated from model-free deterministic replay; shared non-LLM State Evaluator | ACCEPTED BASELINE | ADR-002 |
| Shared Action Gateway, Policy Guard, and Session Controller across discovery, replay, and operator action paths | ACCEPTED BASELINE | ADR-003 |
| Capability Builder, Capability Validator, Capability Store, and typed versioned JSON interpreter | ACCEPTED BASELINE | ADR-004 |
| Asynchronous Playwright Browser Surface Adapter and hybrid observation with validated replay targets | ACCEPTED BASELINE | ADR-005 |
| Explicit control state machine, stale-action rejection, Intervention Manager, and same-live-session Operator Interface | ACCEPTED BASELINE | ADR-006 |
| OpenAI, Anthropic, and hosted Gemma adapters behind a provider-neutral Model Client | ACCEPTED BASELINE | ADR-007 |
| Initial JSON artifact storage and sanitized JSONL evidence | ACCEPTED BASELINE | ADR-008 |
| Required assignment execution path before optional Teams-like voice-and-screen teaching authoring path | ACCEPTED BASELINE | ADR-009 |
| One `src/capability_runner/` package with responsibility-aligned modules and static boundary guardrails | ACCEPTED BASELINE | ADR-010 |

Acceptance records an owner decision. It does not mean the item is implemented or verified.

## Implementation status

| Area | Status | Note |
| --- | --- | --- |
| Architecture and rationale documentation | implemented | P0 documents exist; this describes documentation completion only. |
| P1.0 package/tool foundation | implemented | `pyproject.toml`, real `uv.lock`, local environment configuration, package markers, and repository checks exist. No subsystem behavior is implied. |
| Core Pydantic contracts | implemented | Typed contract models exist for targets, requests, observations, actions, sessions, and run results under `src/capability_runner/contracts/`. |
| Evidence Recorder and redaction | implemented | Typed evidence events are recorded as JSONL under an injected runtime evidence root with pre-write redaction and restricted metadata. |
| Policy Guard | implemented | Typed policy decisions evaluate trusted application/profile context, action kind, semantic click/fill target matches, and normalized URL allowlists with deny-by-default behavior. |
| Session Controller | implemented | In-memory per-session controller enforces control ownership, monotonic generations, and serialized automated dispatch. |
| Synthetic legacy banking demo target | implemented | Flask server-rendered target under `demo_app/` provides member search, results, member details, savings/account views, deterministic fault modes, and read-only synthetic fixtures. |
| Surface abstraction and browser-target contracts | implemented | Typed semantic targets, browser bindings, row-scoped repeated-control references, and a Playwright-free surface adapter port are defined for later browser execution. |
| Async Playwright Browser Surface Adapter and demo target | implemented | P1.5c; the concrete Playwright-backed adapter owns surface mechanics only, while application-specific semantic-to-browser bindings live in test fixtures. |
| Action Gateway integration | implemented | P1.6 Action Gateway resolves trusted semantic bindings, authorizes policy, holds session dispatch ownership during surface execution, and records redacted evidence. |
| Capability definition, Validator, and Store | implemented | P2.1; typed declarative artifacts, structural cross-reference validation, and immutable local JSON version storage are implemented. |
| Deterministic State Evaluator | implemented | P2.2; pure semantic snapshot evaluation classifies declared conditions, terminal states, business outcomes, conflicts, and outputs. |
| Replay Engine | implemented | P2.3; deterministic model-free replay, semantic snapshot collection, bounded observation retry, and Action Gateway integration are implemented and verified. |
| Model Client and provider adapters | implemented | P3.1; provider-neutral Model Client, OpenAI/Anthropic/Gemma HTTP adapters, shared `httpx` transport, explicit provider selection, and mock-based normal tests are implemented and verified. |
| Discovery Engine | implemented | P3.2; bounded semantic observe-decide-act loop, strict untrusted-decision validation, Action Gateway dispatch, and two fresh-session live browser cases are implemented and verified. |
| Capability Builder integration | implemented | P3.3; verified successful discovery traces compile deterministically with trusted authoring metadata, validate through CapabilityValidator, and publish through CapabilityStore. |
| Discovery-to-artifact-to-fresh-replay acceptance | implemented | P3.4; the exact user goal produces trusted required completion evidence, a generated stored artifact, and successful fresh model-free replay for original, different, and business-outcome inputs. |
| Intervention Manager and same-session operator action path | implemented | P4.1 backend; typed lifecycle coordination, controlled operator dispatch, fresh resume validation, and real-browser same-session acceptance. No frontend/operator UI. |
| Minimal local Operator Console | implemented | P4.2; one Flask page and thin API expose safe status, bounded ephemeral same-session PNG views, visible trusted semantic fill/click controls, explicit return, and stop over the frozen P4.1 backend. |
| Approval-blocked Replay continuation | implemented | P4.3; approval-only immutable checkpoints, protected in-memory invocation state, fresh semantic validation, new-generation exactly-once resume through Replay, and same-session Chromium acceptance. |
| Final assignment compliance and readiness audit | implemented | P5.1; strict traceability, system-design, and readiness reports exist under `docs/submission/`. Executive verdict is `NOT READY`; this is not submission acceptance. |
| Reproducibility and demo entry point | implemented | P5.2; `capability-runner demo` exposes verified through-line, intervention, and exception commands with sanitized runtime output under `var/demo-runs/`. |
| Submission documentation and evidence package | implemented | P5.3; evaluator README, exact-heading `REPORT.md`, and genuine curated evidence are present. Local validation passed; public GitHub delivery remains external/manual. |
| Evidence lifecycle and intervention context | implemented | P5.4a; optional passive writers record bounded Discovery/Replay lifecycle and coordinator-owned sanitized intervention context without changing runtime decisions, safety, ownership, or model-free Replay. |
| Optional product/frontend polish | implemented | P5.4b; React/Vite product routes, thin demo-owned HTTP APIs, real Discovery/model-free Replay/same-session Intervention integration, tested responsive states, and four implementation captures are present. Teach remains visual-only. |
| Optional teaching authoring path | not started | Intentionally deferred until the required assignment path is proven and a later phase is authorized. |

## P1.0 verification record

The following narrow repository properties are **VERIFIED BEHAVIOR** on 2026-09-12. This is repository readiness, not application readiness.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Package metadata and import | CPython 3.12.10; `py -3.12 -c <TOML parse and package import check>` | `pyproject.toml` parsed and `capability_runner.__version__` was `0.1.0`. | passed |
| Python syntax | CPython 3.12.10; `py -3.12 -m compileall -q src` and later `tests` | Package markers and tests compiled without errors. | passed |
| Focused smoke/architecture tests | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest tests/smoke tests/architecture` | 5 tests passed in 0.51 seconds. | passed |
| Full current test suite | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest` | Final regression: 5 tests passed in 0.40 seconds. | passed |
| Strict type check | Pyright from locked environment; absolute-path `uv run pyright` | 0 errors, 0 warnings, 0 information messages. | passed |
| Lint | Ruff from locked environment; absolute-path `uv run ruff check .` after local fixes | All checks passed. Initial run found the host-selected `.venv2` plus five test formatting findings; configuration/formatting were corrected and the check was rerun. | passed |
| Dependency lock consistency | uv 0.7.3; absolute-path `uv lock --check` | 15 packages resolved with no lock change required. | passed |
| Dependency footprint | uv 0.7.3; absolute-path `uv tree --depth 1` | One runtime dependency (`pydantic`); development dependencies are `pyright`, `pytest`, and `ruff`. No provider, browser, HTTP, or frontend dependency. | passed |
| Ignore policy | Git 2.50.1 using temporary Git metadata outside the workspace | `.env`, `var/`, assignment text, private Gemma note, and unreviewed reference PNGs were ignored; `.env.example`, curated evidence, and test fixtures were not ignored. | passed |
| Public configuration hygiene | PowerShell content scan over public-facing text/configuration | 0 private Gemma host matches and 0 nonempty API-key placeholder values. | passed |
| Documentation links | PowerShell local-link audit | 15 Markdown files scanned with no missing local target. | passed |
| Editor diagnostics | VS Code workspace diagnostics | No errors found. | passed |

The first plain `uv run pytest tests/smoke tests/architecture` invocation was blocked because the persistent PowerShell session did not resolve `uv` on `PATH`. The same check was rerun with the previously verified absolute uv path and passed; this is a shell-path limitation, not a test pass by inspection.

The first combined ignore-policy audit was invalid because `git check-ignore` requires Git metadata and this workspace is not a Git repository. The check was rerun against temporary Git metadata outside the workspace and passed; the temporary metadata was removed. No repository was initialized and no Git status is available.

No discovery, replay, policy, session-control, browser, provider, handoff, frontend, or end-to-end behavior is **VERIFIED BEHAVIOR**.

## P1.2 verification record

P1.2 status: passed. The evidence recorder writes JSONL only after sanitization, preserves run/session/step/action correlation identifiers, redacts `SecretStr` values, explicit runtime sentinels, and sensitive metadata keys, and rejects unsupported metadata objects and overlong summaries.

The following evidence checks are **VERIFIED BEHAVIOR** on 2026-09-12. They confirm the structured evidence boundary and redaction behavior, not browser screenshots or later richer attachments.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Evidence tests | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest tests/unit/evidence` | 12 tests passed. | passed |
| Full current test suite | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest` | 40 tests passed. | passed |
| Strict lint | Ruff from locked environment; absolute-path `uv run ruff check .` | All checks passed. | passed |
| Strict type check | Pyright from locked environment; absolute-path `uv run pyright` | 0 errors, 0 warnings, 0 information messages. | passed |

The verified redaction boundary is exact-value and sensitive-key based. Known sentinels such as `SUPER_SECRET_TOKEN_9F4A2` and `MEMBER_PRIVATE_74291` are removed before persistence, while identifiers such as `run_id`, `session_id`, `step_id`, and `action_id` remain intact. Richer failure evidence such as browser screenshots, raw DOM snapshots, or provider payloads remains unsupported until later subsystems provide an explicit safe attachment path.

## P1.3 verification record

P1.3 status: passed. Policy Guard evaluates trusted application/profile context, exact target matches for typed surface actions, and normalized navigation destinations with deny-by-default behavior. Untrusted request data cannot authorize itself.

The following policy checks are **VERIFIED BEHAVIOR** on 2026-09-12. They confirm the authorization boundary and navigation semantics, not session ownership, browser dispatch, or evidence emission.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Policy guard tests | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest tests/unit/interaction/test_policy_guard.py` | 19 tests passed. | passed |
| Full current test suite | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest` | 59 tests passed. | passed |
| Strict lint | Ruff from locked environment; absolute-path `uv run ruff check .` | All checks passed. | passed |
| Strict type check | Pyright from locked environment; absolute-path `uv run pyright` | 0 errors, 0 warnings, 0 informations. | passed |

The verified navigation policy uses exact path matching and normalized origin comparison. Unsupported schemes, userinfo tricks, host confusion, and port mismatches are denied. The current trusted target subject is the typed `TargetSpec` itself for click/fill actions; a stable symbolic target identifier is still not present and remains a later surface-adapter concern.

## P1.5a verification record

P1.5a status: passed. The synthetic target application is a local Flask app with a server-rendered shell, iframe work area, read-only member search and account pages, a deterministic permission-denied state, a deterministic session-expired state, and a bounded slow-search scenario.

The following demo-target checks are **VERIFIED BEHAVIOR** on 2026-09-12. They confirm the target surface and fixture behavior, not browser automation.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Demo app tests | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest tests/unit/demo_app/test_demo_app.py` | 16 tests passed. | passed |
| Full current test suite | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest` | 94 tests passed. | passed |
| Strict lint | Ruff from locked environment; absolute-path `uv run ruff check .` | All checks passed. | passed |
| Strict type check | Pyright from locked environment; absolute-path `uv run pyright` | 0 errors, 0 warnings, 0 informations. | passed |
| Dependency lock | absolute-path `uv add flask` | `flask==3.1.3` was added and the lockfile was refreshed. | passed |

The demo target is intentionally read-only. It exposes no member/balance JSON API, no real authentication, and no browser automation. The hidden balances are synthetic fixture data only, and the risky control simulation never mutates those fixtures.

## P1.1 verification record

P1.1 status: passed. The contract aliases now use explicit discriminators, and the raw JSON tests verify supported variants, unknown variants, and missing variant information.

The following contract checks are **VERIFIED BEHAVIOR** on 2026-09-12. They confirm the typed model surface and its validation behavior, not any later engine or UI integration.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Contract tests | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest tests/unit/contracts` | 9 tests passed in 0.30-0.41 seconds across the validation runs. | passed |
| Strict type check | Pyright from locked environment; absolute-path `uv run pyright` | 0 errors, 0 warnings, 0 information messages. | passed |

The contract tests confirmed explicit supported variants, rejection of unknown variants and missing required fields, raw JSON parsing for external inputs, JSON round trips for public values, and redaction of secret-bearing request, action, and observation fields. Sensitive values remain recoverable only from the in-memory `SecretStr` objects, while serialized JSON and `repr()` are redacted.

## Future verification status

| Assumption area | Verification status | Planned evidence |
| --- | --- | --- |
| Modular-monolith concurrency and module boundaries | not run | Event-loop/concurrency measurement, dependency checks, and CLI/web core contract comparison from ADR-001. |
| Model-free replay and shared state classification | not run | Replay with provider access absent, dependency check, unsupported-action rejection, and evaluator fixtures from ADR-002. |
| Gateway parity, policy enforcement, and stale-action rejection | not run | Architecture tests and action authorization matrix from ADR-003. |
| Capability schema expressiveness and reviewability | not run | Serialization/negative validation suite and artifact review exercise from ADR-004. |
| Validated target robustness and surface abstraction | not run | Browser target fixture matrix and second-adapter contract fake from ADR-005. |
| Same-session control transfer and synchronization | passed | P4.1 transition, event-driven race, stale-generation, redaction, dependency, and real Chromium handoff checks passed. Transport disconnect behavior remains unimplemented. |
| Provider adapter compatibility | not run | Contract fixtures plus deployment capability probes from ADR-007. |
| Evidence redaction and file persistence | not run | Canary-secret scan, attachment review, interrupted-write, and concurrent-publication experiments from ADR-008. |
| Author-neutral core for later teaching | not run | Illustrative manually authored candidate through validator/replay contracts from ADR-009. |

## Unresolved implementation details

All entries below are **PROPOSED IMPLEMENTATION DETAIL**, not accepted contracts:

1. PDI-001: exact local synchronization primitive, transition names, ownership principal, and action freshness token.
2. PDI-002: exact Pydantic capability unions, schema migration rules, result variants, and publication validation contract.
3. PDI-003: target candidate ordering, uniqueness thresholds, visual/coordinate restrictions, and tenant override representation.
4. PDI-004: retryable error/observation codes, attempt and backoff bounds, idempotency treatment, and escalation thresholds.
5. PDI-005: evidence field allowlist, screenshot/snapshot masking policy, attachment limits, retention period, and cleanup behavior.
6. PDI-006: normalized Model Client feature contract, provider/model version matrix, and hosted Gemma endpoint capabilities.
7. PDI-007: local same-session operator transport, authentication/authorization contract, disconnect behavior, and exposure boundary.
8. PDI-008: atomic file publication, single-writer enforcement, corruption handling, and retention cleanup limits.
9. Tenant/version profile precedence, product fingerprinting, drift thresholds, quarantine, and override schema; architecture direction is accepted, exact public contract is not.
10. Risk classification and approval semantics for irreversible actions; conservative treatment is accepted, exact policy contract is not.
11. Initial proxy application and concrete goal, provided they exercise a non-trivial flow, business outcome, recoverable condition, hard failure, and handoff without violating site terms.

The P1.0-P6 subdivision sequence is now owner-supplied and recorded in `docs/implementation-plan.md`; it is no longer an unresolved item. The decision register gives constraints, alternatives, recommendations, downsides, and tests for PDI-001 through PDI-008. Items 9 through 11 require records of the same form before they become implementation contracts.

## Unsupported assumptions and contradictions

No contradiction in the accepted baseline has been established. The following remain unsupported until tested:

- one process can coordinate the selected discovery/replay/handoff workload without harmful event-loop blocking;
- the initial action and condition language can represent both the selected happy path and required runtime outcomes;
- hybrid browser observation can consistently produce unique, model-free replay targets;
- all delayed actions can be rejected across ownership transfer;
- the selected OpenAI, Anthropic, and hosted Gemma deployments support the normalized discovery contract;
- sanitized structured evidence and approved visual attachments can avoid persisted secrets and synthetic PII;
- adapter-neutral observations and targets do not embed browser-only assumptions;
- a base vendor capability plus narrow tenant/version profiles can degrade safely across representative variants;
- future human teaching can produce candidates for the same validator/store/policy/replay path without a parallel architecture.

## P1.0 completion and next gate

P1.0 now contains a coherent package/repository structure, a real dependency lock, environment hygiene, dependency and import-side-effect checks, repository mapping, provider/UI requirements, milestone sequence, and subsystem documentation template. Static checks are explicitly limited and no later subsystem has been implemented.

## P1.5b verification record

P1.5b status: passed. The codebase now has typed semantic UI targets, explicit browser target bindings, frame-aware row-scoped repeated-control references, ordered fallback locator semantics, and a pure surface adapter protocol with opaque session references.

The following surface-contract checks are **VERIFIED BEHAVIOR** on 2026-09-12. They confirm the typed abstraction layer and the no-Playwright boundary, not browser execution.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Surface contract tests | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest tests/unit/contracts/test_surface_contracts.py tests/unit/surfaces/test_surface_adapter_contract.py` | passed after the final contract and adapter files were added. | passed |
| Full current test suite | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest` | 94 tests passed. | passed |
| Strict lint | Ruff from locked environment; absolute-path `uv run ruff check .` | All checks passed. | passed |
| Strict type check | Pyright from locked environment; absolute-path `uv run pyright` | 0 errors, 0 warnings, 0 informations. | passed |

P1.6 migrates click/fill policy rules to trusted `SemanticTargetRef` values. Action requests retain their existing operational target fields, but these fields do not control authorization.

## P1.5c verification record

P1.5c status: passed. The concrete Playwright-backed browser surface adapter now drives the synthetic Flask demo through a real Chromium browser, using opaque session refs, isolated browser contexts, typed locator fallback, row-scoped repeated controls, and generic Playwright action handling.

The following real-browser checks are **VERIFIED BEHAVIOR** on 2026-09-12. They confirm the browser adapter and demo target integration, not later gateway, replay, or provider work.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Real-browser adapter integration suite | CPython 3.12.10; workspace venv Python; `pytest tests/integration/surfaces/test_browser_surface_adapter.py -q` | 11 tests passed in 94.79 seconds. | passed |

The browser adapter currently supports the accepted locator vocabulary from P1.5b: role, label, text, CSS, frame context, and row-scoped repeated-control resolution. Unsupported browser surface types still return typed not-supported or target-not-found outcomes instead of leaking raw Playwright objects.

SLOW_SEARCH remains in the demo target as a deterministic scenario for later replay/error-handling work. P1.5c does not require the browser adapter to understand that business condition.

## P1.6 verification record

P1.6 status: passed. `ActionGateway` is the in-process choke point for automated surface side effects: it resolves the binding from the trusted profile, records policy evidence before dispatch, authorizes against the semantic target, and calls `SurfaceAdapter.perform_action` only within `SessionController.automation_dispatch`.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12. They confirm that denied, unbound, stale, and non-automation-controlled requests never reach the surface adapter; same-session dispatches are serialized; fill values are redacted from persisted evidence; and a post-dispatch evidence failure is reported as an action effect that may already have occurred.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Gateway unit and policy suite | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest tests/unit/interaction/test_policy_guard.py tests/unit/interaction/test_action_gateway.py -q` | 26 tests passed. | passed |
| Real-browser gateway integration | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest tests/integration/interaction/test_action_gateway_browser.py -q` | Authorized fill and search click reached the CoreBank results page; persisted evidence did not contain the supplied member ID. | passed |
| Gateway contract/type validation | CPython 3.12.10; absolute-path `uv run pyright` | 0 errors, 0 warnings, 0 informations. | passed |

## P2.2 verification record

P2.2 status: passed. `StateEvaluator` consumes only immutable `EvaluationSnapshot` values containing semantic target observations. It evaluates declared conditions as `TRUE`, `FALSE`, or `UNKNOWN`, classifies success, declared business outcomes, incomplete/unknown states, and conflicts, and extracts declared output values without surface access, model access, persistence, retries, or replay execution.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12. They confirm pure snapshot evaluation and its bounded parser semantics, not browser snapshot collection, profile binding checks, invocation validation, or Replay Engine behavior.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Focused evaluator tests | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest tests/unit/replay/test_state_evaluator.py -q` | 13 tests passed in 0.32-0.46 seconds across final focused runs. Tests include false-success prevention for a wrong member with a valid-looking balance, expected `MEMBER_NOT_FOUND`, terminal conflicts, sensitive in-memory comparison, and Decimal currency conversion. | passed |
| Full repository suite | CPython 3.12.10, pytest 9.1.1; absolute-path `uv run pytest` | 181 tests passed in 86.89 seconds. | passed |
| Strict lint | Ruff from locked environment; absolute-path `uv run ruff check .` | All checks passed. | passed |
| Strict type check | Pyright from locked environment; absolute-path `uv run pyright` | 0 errors, 0 warnings, 0 informations. | passed |
| Dependency lock consistency | uv; absolute-path `uv lock --check` | Lock check completed without changes. | passed |

The evaluator normalizes condition text only by trimming surrounding whitespace. It does not lowercase, strip punctuation, use fuzzy matching, or infer missing values. `currency_minor_units` accepts bounded non-negative USD-style values with exactly two decimal digits, optional `$`, correctly grouped commas, and an optional trailing uppercase currency code; it uses `Decimal` and returns an integer. Output extraction remains separate from terminal classification, so a parseable balance cannot establish success.

## P2.3 verification record

P2.3 status: passed. ReplayEngine executes validated capabilities through the shared ActionGateway, collects semantic snapshots through SnapshotCollector, and uses StateEvaluator for bounded post-action re-observation. Real-browser acceptance and final repository gates passed on 2026-09-12.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Real-browser replay suite | CPython 3.12.10; absolute-path `uv run pytest tests/integration/replay/test_replay_engine_browser.py -q` | 8 tests passed in 61.54 seconds. | passed |
| Full repository pytest | CPython 3.12.10; absolute-path `uv run pytest -q` | 210 tests passed in 165.69 seconds. | passed |
| Ruff | absolute-path `uv run ruff check .` | All checks passed. | passed |
| Pyright | absolute-path `uv run pyright` | 0 errors, 0 warnings, 0 informations. | passed |
| Lock check | absolute-path `uv run lock --check` | Resolved 25 packages in 3ms with no changes. | passed |

Verified replay facts:

- `12345` -> `SUCCESS`, `438221`, `USD`
- `67890` -> `SUCCESS`, `98765`, `USD`
- unknown member -> `BUSINESS_OUTCOME` / `MEMBER_NOT_FOUND`, Search count `1`, Open count `0`
- restricted member -> non-success, not `MEMBER_NOT_FOUND`
- session expired -> non-success, Search count `0`, not `MEMBER_NOT_FOUND`
- slow within bound -> `SUCCESS`, Search count `1`, Open count `1`
- slow beyond bound -> `STEP_TIMEOUT`, Search count `1`, Open count `0`
- model-free real replay passed with model environment variables absent
- `BrowserSurfaceAdapter` has zero application-specific execution branches
- the capability artifact remains hand-authored semantic JSON with no browser locators

## P3.1 verification record

P3.1 status: passed. The discovery layer now exposes a provider-neutral `ModelClient` boundary with OpenAI, Anthropic, and Gemma-compatible HTTP adapters. Provider selection is explicit, fallback is disabled, normal provider tests are mock-based, and replay remains isolated from the model/provider layer.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Focused provider tests | CPython 3.12.10; absolute-path `uv run pytest tests/unit/discovery/test_model_clients.py -q` | 16 tests passed in 1.01 seconds. | passed |
| Ruff | absolute-path `uv run ruff check src/capability_runner/discovery tests/unit/discovery/test_model_clients.py tests/fakes/model_client.py tests/architecture/test_dependency_boundaries.py` | All checks passed. | passed |
| Pyright | absolute-path `uv run pyright src/capability_runner/discovery tests/unit/discovery/test_model_clients.py tests/fakes/model_client.py tests/architecture/test_dependency_boundaries.py` | 0 errors, 0 warnings, 0 informations. | passed |
| Lock check | absolute-path `uv run lock --check` | Resolved 31 packages in 4ms with no changes. | passed |

Verified P3.1 facts:

- provider-neutral ModelClient API: `complete(ModelRequest) -> ModelResponse`
- OpenAI/Anthropic/Gemma adapters implemented with `httpx`
- shared `httpx` transport dependency
- explicit provider selection with no automatic fallback
- normal provider tests use `httpx.MockTransport`
- credential sentinel does not leak
- replay imports no model/provider layer
- normal tests do not require live credentials

## P3.2 verification record

P3.2 status: passed. `DiscoveryEngine` observes only bounded semantic target state, requests one provider-neutral model decision per turn, strictly validates that untrusted decision, grounds fill values and completion evidence, and sends every side effect through `ActionGateway`. It does not import concrete provider adapters or Playwright and does not build or store capability artifacts.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Live ModelClient smoke | Configured local provider; explicit `pytest -m live` selection | Gemma model `gemma4` returned the exact `DISCOVERY_MODEL_OK` response through `ModelClient`; 1 test passed in 2.80 seconds. | passed |
| Live discovery acceptance | Real configured model, real Chromium, synthetic CoreBank app, Browser Surface Adapter, Action Gateway, Policy Guard, Session Controller, and Evidence Recorder; explicit `pytest -m live` selection | 3 tests passed in 27.56 seconds: smoke plus fresh-session discovery for both required members. | passed |
| Discovery safety and architecture | `uv run pytest tests/unit/contracts/test_discovery_contracts.py tests/unit/discovery tests/architecture/test_dependency_boundaries.py -q` | 43 tests passed in 1.45 seconds. | passed |
| Full non-live repository suite | `uv run pytest -q`; default marker excludes `live` | 250 passed and 3 deselected in 159.77 seconds. | passed |
| Ruff | `uv run ruff check .` | All checks passed. | passed |
| Pyright | `uv run pyright` | 0 errors, 0 warnings, 0 information messages. | passed |
| Lock check | `uv lock --check` | 31 packages resolved with no changes. | passed |

Verified P3.2 facts:

- configured provider/model: Gemma / `gemma4`, selected only through trusted local configuration
- `67890` -> `SUCCESS` in 5 turns and 4 gateway actions; current browser state confirmed `$987.65 USD`
- `12345` -> `SUCCESS` in 5 turns and 4 gateway actions in a fresh browser/control session; current browser state confirmed `$4,382.21 USD`
- malformed JSON, selector-shaped targets, unknown targets, ungrounded fills, fabricated/stale completion, no progress, action limits, policy denial, approval, uncertain effects, and trace value leakage are covered by deterministic tests
- normal pytest excludes live tests and does not require configured provider credentials
- returned discovery traces contain no raw goals, model responses, fill values, or observed text
- Discovery Engine imports no concrete provider adapter and neither execution engine calls `SurfaceAdapter.perform_action` directly
- Replay semantics are unchanged
- Capability Builder and reusable artifact generation remain unstarted for P3.3

The first final full-suite attempt ran concurrently with other validation tasks and encountered one existing browser timing failure after 249 passes. That test passed immediately in isolation, and the full non-live suite then passed when rerun alone; only the completed green rerun is used as final acceptance evidence.

## P3.3 verification record

P3.3 status: passed. `CapabilityBuilder` deterministically compiles a verified successful
`DiscoveryResult` plus trusted authoring metadata into the existing `CapabilityDefinition`, then
requires `CapabilityValidator` success before the caller publishes through the existing immutable
`CapabilityStore`. The builder makes zero model/provider calls, performs no browser or filesystem
operations, and does not alter Discovery or Replay behavior.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Focused builder, discovery-regression, store, and architecture suite | CPython 3.12.10; `uv run pytest -q tests/unit/contracts/test_discovery_contracts.py tests/unit/discovery tests/unit/capabilities/test_capability_builder.py tests/integration/capabilities/test_capability_builder_store.py tests/architecture/test_dependency_boundaries.py` | 68 tests passed in 1.77 seconds. | passed |
| Live discovery-to-store proof | Configured real model, real Chromium, synthetic CoreBank app, Browser Surface Adapter, Action Gateway, Policy Guard, Session Controller, Evidence Recorder, CapabilityBuilder, CapabilityValidator, and CapabilityStore; explicit live test selection | 1 test passed in 12.21 seconds. Discovery succeeded in 5 turns and 4 actions; build, validation, immutable save, and load succeeded. | passed |
| Full non-live repository suite | CPython 3.12.10; `uv run pytest -q` | 275 passed and 4 live tests deselected in 163.93 seconds. | passed |
| Ruff | `uv run ruff check .` | All checks passed. | passed |
| Pyright | `uv run pyright` | 0 errors, 0 warnings, 0 information messages. | passed |
| Lock check | `uv lock --check` | 31 packages resolved with no changes. | passed |

Verified P3.3 facts:

- the only automatically derived artifact facts are executed ordered actions, goal-span-backed
	required string inputs, input references, and deterministic semantic step IDs;
- capability/application identity, input sensitivity, success semantics, outputs, business
	outcomes, and replay metadata come only from typed trusted authoring metadata;
- a trusted fixed literal must match fingerprinted current completion evidence, and output source
	targets must be covered by completion evidence;
- invocation-specific member IDs and balances, raw goals and observations, model/provider identity,
	private endpoint data, selectors, fingerprints, and trace internals are absent from stored JSON;
- equivalent successful traces for members `67890` and `12345` produce equal artifact model dumps;
- generated semantics match the existing hand-authored savings-balance reference apart from
	intentionally deterministic generated step identifiers;
- rejected/invalid non-action model entries are excluded, while any non-executed `ACT` entry in an
	alleged successful result causes a fail-closed trace-integrity error;
- architecture checks enforce that CapabilityBuilder has no Discovery runtime, ModelClient,
	provider, BrowserSurfaceAdapter, Playwright, or CoreBank-specific production dependency;
- Replay code and behavior are unchanged, and no generated artifact was replayed.

The first live P3.3 attempt reached the correct browser state but the shorter goal did not yield
completion evidence for every trusted success target. CapabilityBuilder correctly rejected it with
`BUILD_COMPLETION_EVIDENCE_MISSING`. A rerun whose natural-language goal explicitly requested member
identity, `Savings` account type, and balance produced the required evidence and passed. Discovery
behavior was not modified.

## P3.4 verification record

P3.4 status: passed. The backward-compatible P3.2 correction adds trusted, default-empty
`required_completion_targets` to DiscoveryRequest. Discovery rejects profile-unknown requirements
before execution and uses the existing bounded repair loop when grounded `COMPLETE` evidence omits
a required target. Builder validation and Replay behavior are unchanged.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Completion-target and frozen-boundary regression | CPython 3.12.10; `uv run pytest -q tests/unit/contracts/test_discovery_contracts.py tests/unit/discovery tests/unit/capabilities/test_capability_builder.py tests/architecture/test_dependency_boundaries.py` | 72 passed in 1.95 seconds. Missing evidence repaired without a gateway action; stale evidence failed; unknown requirements failed before model/gateway execution; empty requirements preserved prior behavior; Builder checks remained green. | passed |
| Live generated-artifact through-line | Configured Gemma / `gemma4`, real Chromium, exact goal `Find the savings balance for member 67890.`, real DiscoveryEngine and shared ActionGateway; explicit live test selection | 1 passed in 34.69 seconds. Discovery used 5 model calls and 4 UI actions and verified identity, account type, and balance. The generated artifact validated, saved, reloaded, and produced fresh model-free results `12345 -> 438221 USD`, `67890 -> 98765 USD`, and unknown member -> `MEMBER_NOT_FOUND`. | passed |
| Full non-live repository suite | CPython 3.12.10; `uv run pytest -q` | 280 passed and 5 live tests deselected in 158.40 seconds. | passed |
| Ruff | `uv run ruff check .` | All checks passed. | passed |
| Pyright | `uv run pyright` | 0 errors, 0 warnings, 0 information messages. | passed |
| Lock check | `uv lock --check` | 31 packages resolved unchanged in 6 ms. | passed |

Verified P3.4 facts:

- the natural-language goal remained the exact short balance request;
- trusted authoring metadata, not model output, supplied required completion targets;
- required targets described evidence only and did not prescribe actions or selectors;
- CapabilityBuilder retained independent identity, literal, and output-source validation;
- the serialized generated artifact crossed CapabilityStore before Replay;
- discovery browser/control state was destroyed before replay;
- each replay used a new browser context, control session, ActionGateway, and PolicyGuard;
- Discovery made 5 model calls, Builder made 0, and Replay made 0;
- the artifact omitted invocation values, observed balance, provider/model identity, private endpoint,
  selectors, and raw DiscoveryTrace data;
- replay remained statically isolated from Discovery/model/provider imports.

The initial P3.4 attempt remains relevant failure evidence: before the correction, the same goal
produced identity and balance evidence but omitted account type, and Builder correctly failed closed
with `BUILD_COMPLETION_EVIDENCE_MISSING`. No Builder check was weakened to obtain the pass.

P3.4 PASS is recorded. P3 is complete and frozen.

## P4.1 verification record

P4.1 status: passed for backend same-session human handoff. Session Controller remains the sole
owner of lifecycle, ownership, generation, and dispatch serialization. Intervention Manager
coordinates those transitions, Operator Action Gateway applies policy and evidence controls to
manual typed actions, and an injected validator must freshly inspect current state before resume.
No Discovery, Builder, Replay, provider, frontend, or operator UI implementation changed.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Focused P4.1 acceptance | CPython 3.12.10; `uv run pytest -q tests/unit/interaction/test_session_controller.py tests/unit/intervention tests/architecture/test_dependency_boundaries.py::test_intervention_is_engine_provider_and_concrete_browser_neutral tests/integration/intervention/test_human_handoff_browser.py` | 38 passed in 8.19 seconds. Covered lifecycle, terminal behavior, wrong-owner and stale-generation rejection, explicit-value redaction, event-driven bidirectional concurrency, forbidden imports, and real Chromium handoff. | passed |
| Full non-live repository suite | CPython 3.12.10; `uv run pytest -q` | 299 passed and 5 live tests deselected in 176.50 seconds. | passed |
| Ruff | `uv run ruff check .` | All checks passed. | passed |
| Pyright | `uv run pyright` | 0 errors, 0 warnings, 0 information messages. | passed |
| Lock check | `uv lock --check` | 31 packages resolved unchanged in 5 ms. | passed |

Verified P4.1 facts:

- automation and operator actions share one dispatch lock and cannot overlap;
- pause invalidates the prior generation, grant transfers ownership only after quiescence, return
	waits for operator quiescence, and successful fresh validation resumes at a new generation;
- the original automation run identity is restored rather than replacing it with operator identity;
- wrong-owner, stale-generation, wrong-state, terminal, policy-denied, and unbound actions fail
	closed before reaching the surface;
- the sensitive sentinel `OPERATOR_PRIVATE_VALUE_61937` is absent from result representations and
	persisted evidence;
- intervention production files have no concrete browser, Playwright, Discovery, Replay, Model
	Client, or provider imports;
- real Chromium acceptance preserved one opaque `SurfaceSessionRef`: automation filled `12345`,
	the operator changed it to `67890`, fresh post-return inspection observed `67890`, resume restored
	automation at generation 3, and the old generation was rejected;
- the persisted browser-acceptance evidence contains neither `12345` nor `67890`.

At P4.1 acceptance, PASS was recorded for backend handoff only; no frontend/operator UI or later
P4 work had started. P2 and P3 remain complete and frozen.

## P4.2 verification record

P4.2 status: passed for the minimal local Operator Console. The dependency-light page and Flask
API are adapters over an application service that resolves the trusted intervention record,
profile, operator identity, generation, and same `SurfaceSessionRef` server-side. Typed fill/click
actions delegate to the frozen Operator Action Gateway. Return delegates to Intervention Manager
and stops at `resume_requested`; no fresh validation or engine continuation occurs.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Focused P4.2 plus P4.1 regression | CPython 3.12.10; `uv run pytest -q tests/unit/contracts/test_surface_contracts.py tests/unit/interfaces/test_operator_http.py tests/unit/interaction/test_session_controller.py tests/unit/intervention tests/integration/surfaces/test_browser_surface_adapter.py::test_operator_view_is_bounded_ephemeral_and_rejects_closed_session tests/integration/interfaces/test_operator_console_browser.py tests/architecture/test_dependency_boundaries.py` | 83 passed in 20.02 seconds. | passed |
| Real rendered operator-console flow | Flask HTTP on localhost, real Chromium target session, second headless Chromium rendering the operator page, real Session Controller, Intervention Manager, Policy Guard, and Operator Action Gateway | 1 passed. The page loaded a non-empty current PNG, filled `67890`, clicked Search, cleared the fill field, returned control, and showed `Resume validation required`. Fresh inspection on the same surface reference observed `67890`. | passed |
| Full non-live repository suite | CPython 3.12.10; `uv run pytest -q` | 314 passed and 5 live tests deselected in 187.30 seconds. | passed |
| Ruff | `uv run ruff check .` | All checks passed. | passed |
| Pyright | `uv run pyright` | 0 errors, 0 warnings, 0 information messages. | passed |
| Lock check | `uv lock --check` | 31 packages resolved unchanged in 3 ms. | passed |

Verified P4.2 facts:

- `/operator/interventions/{intervention_id}` serves one local operator page; there is no dashboard,
	capability editor, Discovery UI, Replay library, teaching UI, or React build;
- status JSON omits operator ID and surface-session ID, while all view/action requests bind to the
	immutable server-held intervention record;
- strict action JSON accepts only semantic `fill` and `click`; surface IDs, raw selectors, unknown
	targets, extra fields, click values, navigation, scripts, coordinates, and arbitrary actions are
	rejected before dispatch;
- available controls are registered presentation controls whose trusted profile targets are
	currently `VISIBLE`; unavailable or ambiguous targets are not presented;
- HTTP/application code contains no direct `perform_action` call and imports no Playwright,
	Browser Surface Adapter, Discovery, Replay, Model Client, or provider module;
- browser views are read-only in-memory PNG responses, bounded to 1600 by 1200 and 2 MB, marked
	`no-store`, and not persisted or sent to Evidence Recorder;
- action attempts fail closed unless the registered operator currently owns the session;
- return control reaches `resume_requested` only, and P4.2 makes zero model calls and zero resume
	validation calls;
- real Chromium acceptance used the identical opaque `SurfaceSessionRef` before, during, and after
	operator HTTP actions; automation filled `12345`, the human changed it to `67890`, and fresh
	semantic inspection observed `67890`;
- sensitive fill sentinels and both real-browser fill values were absent from response/evidence
	bytes.

The console is local/demo scoped and unauthenticated. Production deployment would require
authenticated operator identity, tenant/session authorization, TLS, CSRF protection, and a durable
registration/session transport. P4.2 does not weaken server-side intervention/session binding.

At P4.2 acceptance, PASS was recorded with P2, P3, and P4.1 frozen; P4.3 and the final product UI
had not started.

## P4.3 verification record

P4.3 status: passed for `APPROVAL_REQUIRED` Replay continuation. Action Gateway returns approval
before surface dispatch, so Replay emits an immutable checkpoint with `NOT_EXECUTED` effect state.
All other failures, including uncertain post-dispatch effects, have no auto-resumable checkpoint.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Focused P4.3 plus P4.1/P4.2 regression | CPython 3.12.10; `pytest -q tests/unit/replay/test_replay_engine.py tests/unit/application/test_run_coordinator.py tests/unit/intervention tests/unit/interfaces/test_operator_http.py tests/integration/intervention/test_human_handoff_browser.py tests/integration/interfaces/test_operator_console_browser.py tests/end_to_end/test_replay_intervention_resume.py tests/architecture/test_dependency_boundaries.py` | 70 passed in 36.67 seconds. | passed |
| Real same-session Replay/operator/resume | Flask HTTP, real Chromium, real capability, Replay Engine, State Evaluator, Snapshot Collector, Action Gateways, Policy Guards, Session Controller, Intervention Manager, P4.2 API, and Browser Surface Adapter | 1 passed in 8.57 seconds. Automation stopped before Savings; P4.2 HTTP clicked it once; fresh validation restored generation 3; Replay returned `SUCCESS`, `98765`, `USD` without dispatch. | passed |
| Full non-live repository suite | CPython 3.12.10; `uv run pytest -q` | 329 passed and 5 live tests deselected in 191.76 seconds. | passed |
| Ruff | `uv run ruff check .` | All checks passed. | passed |
| Pyright | `uv run pyright` | 0 errors, 0 warnings, 0 information messages. | passed |
| Lock check | `uv lock --check` | 31 packages resolved unchanged in 4 ms. | passed |

Verified P4.3 facts:

- `ReplayResult` identifies the approval-blocked step and carries a checkpoint only when the action
	is definitely not executed;
- `ACTION_EFFECT_OCCURRED_EVIDENCE_FAILED` and all other uncertain/non-approval failures are not
	auto-resumable;
- the coordinator requests intervention with safe `APPROVAL_REQUIRED` copy and binds the immutable
	P4.1 record to the existing runtime surface reference;
- P4.1's injected validator collects fresh capability-semantic state while automation remains
	blocked, then Session Controller restores automation with a new generation;
- Replay resume collects fresh state again and evaluates terminal conditions first; a successful
	terminal state extracts real observed outputs without dispatching the blocked step;
- when terminal state is incomplete, a true deterministic blocked-step postcondition advances to
	the next step, a false postcondition re-enters normal policy once, and unknown/absent proof does
	not dispatch blindly;
- previous Replay steps are excluded by the checkpoint cursor and are not repeated;
- repeated approval creates one new intervention and returns; there is no automatic loop or policy
	bypass;
- an `asyncio.Lock` plus consumed tombstone permits one of two racing resumes to execute Replay;
- stopping the P4.1 session invalidates the continuation and dispatches no action;
- protected runtime inputs use repr-hidden `SecretStr` values, are cleared from pending storage on
	consumption, and are absent from public result/checkpoint representations and evidence;
- the continuation coordinator imports no Discovery, Model Client, provider adapter, Playwright,
	or concrete Browser Surface Adapter and contains no direct surface action call;
- the real acceptance kept one opaque `SurfaceSessionRef` throughout. Automation executed member
	fill, Search, and Open result once each and Savings zero times; the operator executed Savings
	once; resumed Replay executed no action and returned `98765` / `USD`;
- generation 0 was rejected as stale after generation 3 became current;
- no model call occurred.

Existing gateway and intervention events provide correlated handoff/action evidence. P4.3 does not
add duplicate coordinator event types. The continuation registry is local, in-memory, and not
crash-recoverable. Only `APPROVAL_REQUIRED` is supported as a resumable reason.

P4.3 PASS is recorded. P4 is complete and frozen.

## P5.1 audit record

P5.1 status: completed documentation audit. The repository was evaluated against the original
assignment rather than the internal milestone sequence. The result is **NOT READY**: 23 of 30
mandatory traceability rows pass, 4 are partial, and 3 are missing. This audit does not change the
P1-P4 implementation or verification status.

The audit artifacts are:

- `docs/submission/requirement-traceability.md`;
- `docs/submission/system-design.md`;
- `docs/submission/readiness-report.md`.

Fresh P5.1 checks on 2026-09-12:

| Check | Observed result | Status |
| --- | --- | --- |
| Live test collection | `pytest --collect-only -m live -q` collected 5 live cases from 334 total; no provider test executed. | passed |
| Environment-template shape | All eight provider variable names documented in `docs/providers.md` are present in `.env.example`; values are empty/placeholders. | passed |
| Submission inventory | Root `REPORT.md` absent; `/evidence/` has no generated artifact or run logs; no product discovery/replay command entry point exists. | blocking findings recorded |
| Evidence implementation audit | Persisted production events originate from automated/operator gateways and Intervention Manager; Discovery decision rationale and Replay lifecycle/outcome events are not directly recorded. | partial requirement recorded |
| Rich failure evidence audit | Browser adapter can produce bounded textual failure state, but no production call site invokes or persists it. | partial requirement recorded |
| Intended-public text hygiene | After removing three historical workstation paths, scans found no Windows user paths, non-loopback private IPv4 URLs, likely credential assignments, or bearer-token patterns. | passed |
| Documentation diagnostics | New P5.1 Markdown files reported no editor diagnostics. | passed |

No source, test, package configuration, or lock file changed in P5.1. The latest executable runtime
baseline therefore remains the P4.3 gate: 329 ordinary tests passed with 5 live tests deselected,
Ruff passed, Pyright reported 0 errors and 0 warnings, and `uv lock --check` resolved 31 packages
unchanged. At the time of that audit, P5.2, P5.3, and P5.4 were defined but not started.

## P5.2 verification record

P5.2 status: passed. The packaged `capability-runner` script composes the frozen P1-P4 components
through three stable demo commands. Each command owns its loopback server and Chromium lifecycle,
writes sanitized ignored runtime output beneath `var/demo-runs/<run-id>/`, and returns a nonzero
status unless its expected outcome is verified.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Environment and command | Observed result | Status |
| --- | --- | --- | --- |
| Focused public demo composition | CPython 3.12.10; public `main()` composition; `pytest -q tests/unit/interfaces/test_demo_cli.py tests/live/demo/test_demo_through_line.py -m "live or not live"` | 5 passed in 33.79 seconds. Help, safe missing configuration, exception, intervention, and live through-line behavior passed. | passed |
| Live reviewer through-line | Configured Gemma / `gemma4`; `capability-runner demo through-line`; real Chromium and loopback CoreBank | Discovery `SUCCESS` in 5 model calls; generated artifact stored and reloaded; Discovery session destroyed; fresh Replay for `12345` returned `SUCCESS`, `438221`, `USD`; Builder and Replay model calls were 0. | passed |
| Same-session intervention command | `capability-runner demo intervention`; real Chromium and existing P4.2 operator HTTP API | `APPROVAL_REQUIRED`; same surface reference; operator Savings click; fresh validation advanced generation `0 -> 3`; Replay returned `SUCCESS`, `98765`, `USD`; no prior automation side effect repeated. | passed |
| Exceptional outcome command | `capability-runner demo exception`; real Chromium; no Model Client | Replay returned `BUSINESS_OUTCOME` / `MEMBER_NOT_FOUND`; sanitized summary and JSONL evidence were written. | passed |
| Rich terminal failure evidence | Existing `session_expired` demo mode through the reviewer Replay composition | Replay returned terminal `FAILURE` / `TARGET_NOT_FOUND`; the runtime persisted a bounded sanitized `reviewer-demo` error event containing current surface state. | passed |
| Full ordinary repository suite | CPython 3.12.10; `uv run pytest -q` | 333 passed and 6 live tests deselected in 244.36 seconds. | passed |
| Ruff | `uv run ruff check .` | All checks passed. | passed |
| Pyright | `uv run pyright` | 0 errors, 0 warnings, 0 information messages. | passed |
| Lock consistency | `uv lock --check` | 31 packages resolved unchanged in 5 ms. | passed |

Verified P5.2 facts:

- only through-line Discovery creates a Model Client; Builder, Replay, intervention, and exception
	paths remain model-free;
- the generated capability contains no discovery member/balance value, browser selector, or
	provider/model identity;
- through-line destroys Discovery control/browser state before opening a fresh Replay adapter and
	control session on the same persistent application event-loop runner;
- intervention uses the existing operator HTTP API, Session Controller, Operator Action Gateway,
	Intervention Manager, and continuation coordinator rather than duplicating their behavior;
- `MEMBER_NOT_FOUND` is recorded as a business outcome, while genuine terminal automation failure
	invokes bounded failure-surface capture;
- summaries contain only portable relative artifact/evidence paths and tested runtime output
	contains no synthetic member IDs, credentials, private endpoint, or developer path;
- the root README, root `REPORT.md`, curated `/evidence/`, complete Discovery reasoning/lifecycle
	evidence, complete public intervention context, and public repository delivery remain unresolved.

P5.2 PASS remains the frozen runtime baseline for the P5.3 packaging work below.

## P5.3 verification record

P5.3 local packaging status: passed with external delivery outstanding. Runtime semantics, source,
tests, package configuration, and lock data were not changed. The P5.2 full gates therefore remain
the current runtime baseline.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Observed result | Status |
| --- | --- | --- |
| Required report structure | `REPORT.md` contains exactly the seven assignment headings in the required order. | passed |
| Curated evidence provenance | Six source-to-curated SHA-256 comparisons returned true; generated JSON was not edited. | passed |
| Evidence integrity | Required files exist; all JSON and JSONL parse; the untouched through-line summary's relative artifact/evidence paths resolve. | passed |
| Documentation links | 28 repository-owned Markdown files were scanned with no missing local target. | passed |
| Public-text portability/privacy | 156 intended-public text files contained no developer Windows path, full private IPv4 address, or bearer token; corrected full-address patterns avoided version/heading false positives. | passed |
| Secret hygiene | No high-confidence provider/Git/AWS/Google/private-key signature was found; credential-bearing `.env.example` values are empty or placeholders. | passed |
| Reviewer help | `capability-runner --help` and `capability-runner demo --help` completed and list the three stable commands. | passed |
| Focused public CLI regression | `uv run pytest -q tests/unit/interfaces/test_demo_cli.py` completed with 4 passed in 14.42 seconds. | passed |
| Fresh exceptional outcome | `capability-runner demo exception --output-root var/demo-runs` returned `BUSINESS_OUTCOME / MEMBER_NOT_FOUND` with zero model calls and produced the curated summary/log. | passed |
| Fresh intervention | `capability-runner demo intervention --output-root var/demo-runs` produced a summary with same-session `SUCCESS`, generation `0 -> 3`, `98765 / USD`, zero model calls, and no repeated automation side effects. | passed |
| Public repository | No `.git/` metadata or public URL is present in this workspace. No repository was initialized or pushed. | EXTERNAL-MANUAL |

The mandatory assignment matrix is now 27 PASS, 2 PARTIAL, and 1 MISSING. E-01 and H-02 remain
partial by design and are disclosed in the README/report. L-04 remains missing until the owner
reviews intended Git contents, publishes the repository, and verifies anonymous access. P5.4 and
later work remain unauthorized.

## P5.4a verification record

P5.4a status: passed. This separately authorized slice added passive evidence observability and
curated fresh model-free runs. It did not change Discovery decisions, Replay interpretation,
policy outcomes, action dispatch, control ownership, continuation semantics, or provider behavior.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Observed result | Status |
| --- | --- | --- |
| Focused evidence regression | Discovery, Replay, continuation-coordinator, and reviewer CLI modules completed with 60 passed in 23.63 seconds. | passed |
| Full ordinary repository suite | JUnit recorded 335 tests, 0 failures, 0 errors, and 0 skipped in 202.542 seconds; collection confirmed 335 selected and 6 live deselected. | passed |
| Ruff | `uv run ruff check .` returned `All checks passed!`. | passed |
| Pyright | `uv run pyright` returned 0 errors, 0 warnings, and 0 information messages. | passed |
| Lock consistency | `uv lock --check` resolved 31 packages unchanged. | passed |
| Fresh exceptional outcome | Genuine Chromium run `exception-0c1ac850090a45b887b05e2bf35c2a26` returned `BUSINESS_OUTCOME / MEMBER_NOT_FOUND`, two actions, and zero model calls with complete Replay lifecycle. | passed |
| Fresh intervention | Genuine Chromium run `intervention-fa70344b2855484b831836b4e7c3d3ca` proved approval, same-session operator action, generation `0 -> 3`, resumed `SUCCESS`, `98765 / USD`, zero model calls, and no repeated automation side effects. | passed |
| Curated provenance | The fresh exception and intervention summary/JSONL pairs produced four source-to-curated SHA-256 equality results of true. | passed |
| Evidence integrity and privacy | All 8 curated JSON/JSONL files parsed; scans found zero synthetic private values, developer paths, private endpoints, bearer tokens, raw goals/runtime inputs, provider payloads, or selector fields. | passed |
| Documentation links | 38 repository Markdown files containing 24 links were checked with no missing local target. | passed |
| Provider availability | Provider selection and checked OpenAI, Anthropic, and Gemma configuration values were absent; no paid/live Discovery was attempted and no new Discovery evidence is claimed. | constrained |
| Editor diagnostics | Workspace and touched-file diagnostics reported no errors. | passed |

The mandatory assignment matrix is now 28 PASS, 1 PARTIAL, and 1 MISSING. H-02 moves to PASS
because the curated intervention chronology carries the required bounded context without runtime
values. E-01 remains PARTIAL until a configured provider permits a genuine refreshed Discovery
run containing the implemented lifecycle and decision metadata. L-04 remains the external/manual
public-repository delivery action. Broad P5.4 polish and P6 remain unauthorized.

## P5.4a.1 verification record

P5.4a.1 status: passed. No source, tests, contracts, dependencies, or runtime semantics changed;
only genuine curated through-line files and status documentation were refreshed.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Observed result | Status |
| --- | --- | --- |
| Neutral live ModelClient smoke | Existing live smoke passed against provider `gemma`, model `gemma4`: 1 passed in 3.23 seconds. | passed |
| Public reviewer through-line | `uv run capability-runner demo through-line` completed genuine Discovery `SUCCESS` in 5 model calls, capability build/store/load, and fresh model-free Replay `SUCCESS` with 8 total browser actions and `438221 / USD`. | passed |
| Bounded transient failures | The first two reviewer attempts each executed one real bounded semantic action and then ended safely with `MODEL_TIMEOUT` on turn 2; neither was curated. A third unchanged invocation passed. | recorded |
| Lifecycle chronology | Curated JSONL contains `DISCOVERY_STARTED`, observation and five `DISCOVERY_DECISION_RECEIVED` events, `DISCOVERY_COMPLETED`, `CAPABILITY_BUILD_STARTED`, `CAPABILITY_VALIDATED`, `CAPABILITY_STORED`, `CAPABILITY_LOADED`, and complete Replay step/terminal events in order. | passed |
| Focused evidence regression | Evidence/redaction plus targeted Discovery, Replay, continuation, exception, and intervention evidence checks completed with 17 passed in 31.32 seconds. | passed |
| Curated provenance | Summary, evidence JSONL, and generated capability each match the successful runtime source byte-for-byte by SHA-256. | passed |
| Parse and privacy | All three curated through-line files parse; exact configured endpoint/key checks and pattern scans found zero private endpoint, credential/token, Windows path, sensitive member value, raw model field, raw goal/input map, HTML, or selector matches. | passed |
| Reused regression baseline | No source or tests changed. The P5.4a baseline remains 335 ordinary tests passed, 6 live deselected, Ruff passed, Pyright 0 errors/0 warnings, and lock resolved 31 packages unchanged. | passed |

The mandatory assignment matrix is now 29 PASS, 0 PARTIAL, and 1 MISSING. E-01 moves to PASS.
L-04 public repository delivery remains the sole missing requirement and requires owner action.
Broad P5.4 polish and P6 remain unauthorized.

## P5.4b verification record

P5.4b implementation status: implemented. This authorized optional slice adds a React/Vite
product surface and demo-owned thin HTTP composition. It does not change Replay interpretation,
policy decisions, Action Gateway ownership, intervention continuation semantics, curated E-01/H-02
evidence, or the mandatory assignment verdict. Teach is visual-only; P6 has not started.

The following checks are **VERIFIED BEHAVIOR** on 2026-09-12.

| Check | Observed result | Status |
| --- | --- | --- |
| Focused product backend | Artifact index, product HTTP, and CLI regression completed with 11 passed. | passed |
| Frontend behavior | Vitest/Testing Library completed 7 tests covering backend-owned overview data, navigation, capability schema/steps, business outcomes and sanitized lifecycle, masked Replay input, historical intervention safety, safe errors, and Discovery submission. | passed |
| Frontend typecheck | `npm --prefix web run typecheck` completed with no TypeScript errors. | passed |
| Frontend production build | Vite transformed 1604 modules and produced the static bundle successfully. | passed |
| Ruff | Full repository `ruff check` returned `All checks passed!` after one import-order correction. | passed |
| Pyright | Full repository `pyright` returned 0 errors, 0 warnings, and 0 information messages. | passed |
| Lock consistency | `uv lock --check` resolved 31 packages unchanged. | passed |
| CLI compatibility | `capability-runner --help` completed and retained the `demo` command; focused CLI tests are included in the 11-test product regression. | passed |
| Reference capture | The four real-route PNGs under `docs/references/ui/implemented/` each report exactly `1448 x 1086`. | passed |
| Live intervention UI | Capture started the existing managed handoff, rendered its current bounded `SurfaceView` and trusted semantic controls, and stopped it in cleanup. | passed |
| Responsive overflow | `/`, `/discover`, `/capabilities`, `/runs`, and `/interventions` loaded at `390 x 844` with document width no greater than viewport width. | passed |
| Visual comparison | Home, capability library, and live intervention are PASS. Persisted run detail is PARTIAL because it truthfully substitutes sanitized evidence for the reference's unavailable live preview. No major FAIL remains. | passed |
| Full ordinary Python suite | Resource-isolated rerun completed 342 passed and 6 live deselected in 323.86 seconds. An earlier concurrent run had one 2-second Chromium navigation timeout after 341 passes; that exact test then passed alone in 14.07 seconds. | passed |
| Production server smoke | The built client loaded from `http://127.0.0.1:5000/`, and `/api/overview` returned public backend-derived counts and recent summaries. | passed |

Verified product boundaries:

- all displayed capabilities, summaries, events, controls, and counts come from validated local
	artifacts or existing runtime services;
- Discovery delegates to the configured provider path, while Replay remains model-free;
- browser and operator side effects remain behind the existing Action Gateway and Operator Console;
- active SurfaceViews are ephemeral and cache-disabled; historical runs never fabricate imagery;
- client errors are bounded summaries, replay input is masked and not echoed, and no provider
	configuration is exposed;
- production code under `src/capability_runner/` imports neither `demo_app` nor frontend code.

The repeatable capture and fidelity evidence are recorded in
`docs/ui/visual-fidelity-report.md`. P6 remains unauthorized and unimplemented.

## Generic Discovery milestone verification record

Design: **ACCEPTED BASELINE** (owner's attached milestone request, 2026-09-12).
Implementation: implemented. Verification: passed for the documented bounded browser scope.
The pre-edit audit and contracts are in `docs/subsystems/generic-discovery.md`.

Completed checks are **VERIFIED BEHAVIOR**:

| Check | Actual result | Evidence |
| --- | --- | --- |
| Initial trusted surface regression | 37 passed; two Chromium navigation failures exceeded the pre-existing 2-second timeout. These require isolated rerun. | Session test output; not a full passing gate. |
| First unprofiled snapshot/reference browser check | 1 passed in 21.71s. No target bindings existed at session creation. | `tests/integration/surfaces/test_generic_browser.py` |
| Scripted unprofiled package and fresh Replay | 1 passed in 38.52s; different input returned 438221/USD and model-call count did not increase. | `tests/integration/capabilities/test_generic_package.py` |
| Contract, bounds, policy and genericity architecture tests | 30 passed in 1.76s. | `var/generic-safety-unit.txt` |
| Real-browser generic package and safety checks | 4 passed in 129.20s; hidden/duplicate controls, stale references, prompt injection, wrong entity, application mismatch, generated package and fresh Replay. | `var/generic-browser-tests.txt` |
| Product API and existing architecture checks | 12 passed in 10.79s. | `var-generic-fast.tmp` |
| CoreBank real-provider acceptance | SUCCESS with paraphrased goal; generated capability; different-input fresh Replay 438221/USD and zero Replay model calls. | `var/evals/eval-6388d04be8a1453ca875a93a5917f2c2/report.json` |

The same early live report failed LegacyBank B (bounded repeated fill). Other attempts returned
provider timeout/error or rejected completion evidence. These are not PASS. Reports retain every
attempt locally. Subsequent completed checks are recorded below, independently of those failures.

| Check | Actual result | Evidence |
| --- | --- | --- |
| LegacyBank B real-provider acceptance | PASS: zero pre-existing targets, real Gemma Discovery in 4 calls / 3 actions, generated package stored, fresh Replay using 12345 returned 438221/USD with zero model calls. Only the bank-b-live case in this report passed; its CoreBank case failed at the provider. | `var/evals/eval-cb90391893d64feb8d51dc29eab1985c/report.json` |
| CoreBank real product UI | PASS: arbitrary paraphrase submitted, 5 real model calls, 8 distinct rendered live frames from one session, capability displayed, new-input Replay 438221/USD / zero calls, unknown input MEMBER_NOT_FOUND. | `var/manual-corebank-known.json`; `docs/references/ui/implemented/generic-discovery/corebank-known-*.png` |
| Same-session HITL through product controls | PASS: operator Savings action, return control, fresh validation, generation 0 to 3, SUCCESS / 98765 USD, no repeated automation action, zero Replay calls. | `var/manual-handoff.json`; `docs/references/ui/implemented/generic-discovery/handoff-*.png` |
| Mobile routes | PASS: Home, Discover, Capabilities, Runs and Interventions have no horizontal document overflow at 390 x 844. | `var/manual-handoff.json` |
| Preview/reference race regression | PASS: capture_view preserves a current ephemeral ref; actual DOM replacement still invalidates it. Caret hiding during screenshot capture had mutated the DOM; capture now preserves caret/animation state. | `var/preview-freshness-test.txt`; full suite below |
| Full ordinary Python suite | 371 passed, 8 live deselected in 274.32s. Includes original trusted-profile, Replay, policy, session, evidence and HITL regressions. | `var/pytest-generic-final.txt` |
| Evaluation metric follow-up | 3 passed in 1.07s after preserving running timeouts and counting false Discovery success as well as false Replay success. Unsafe executed actions fail evaluation. | `var/eval-unit-final.txt` |
| Frontend gates | 7 tests passed; TypeScript typecheck passed; production bundle built. | `var/frontend-tests-final.txt`, `var/frontend-typecheck-final.txt`, `var/frontend-build-final.txt` |
| Static and dependency gates | Ruff all checks passed; Pyright 0 errors / 0 warnings; uv lock --check resolved 31 packages unchanged. | `var/ruff-generic-final.txt`, `var/pyright-generic-final.txt`, `var/lock-generic-final.txt` |
| Public CLI compatibility | Root, demo and eval --help commands completed successfully. | `var/cli-help.txt`, `var/cli-demo-help.txt`, `var/cli-eval-help.txt` |
| Normal Discovery evaluation | 13/13 cases passed; nine fresh Replay results matched expectations (including one business outcome), three generated profiles validated, zero false/wrong-entity successes, unsafe actions or Replay model calls. | `var/evals/eval-b545adee71e8401eb6ce053c7e070c54/report.json` |
| LegacyBank B real product UI | PASS: no pre-existing target profile; 4 real Gemma calls / 3 actions; 9 distinct rendered live frames from one session; generated profile/capability stored; fresh Replay input 12345 returned 438221/USD with zero model calls. | `var/manual-bank-b.json`; `docs/references/ui/implemented/generic-discovery/bank-b-*.png` |
| Normal Replay evaluation command | 13/13 cases passed, goal_success_rate 1.0 (9 positive preparations), 9 expected fresh Replay results / 9, three generated profiles, zero false successes, wrong-entity successes, unsafe actions, timeouts or Replay model calls. Average scripted turns 3.923; actions 2.846 across all 13 cases. | `var/evals/eval-741f10d3c6d1440da11dab81db0e9b5b/report.json`; `var/eval-replay-final.txt` |
| Persisted package independence | Saved LegacyBank-B package loaded and replayed in a new DiscoveryWorkspace with an empty provider environment. SUCCESS / 438221 USD / zero model calls. | `var/stored-package-replay.json`; `var/stored-package-replay-output.txt` |
| Final frontend recheck | 7 tests passed in 15.95s; typecheck passed; production bundle built in 4.55s. | `var/frontend-tests-generic-final.txt`, `var/frontend-typecheck-generic-final.txt`, `var/frontend-build-generic-final.txt` |

The two completed product UI acceptance runs are `discovery-f43c14812ad44cd1b84a928630f4d710`
(CoreBank, `workflow_b84a928630f4d710` v1.0.0) and
`discovery-4dbcf55534f544f091489132f93f9f51`
(LegacyBank B, `workflow_91489132f93f9f51` v1.0.0). Their real packages are under the
corresponding `var/demo-runs/<run-id>/capabilities/` directories. This is two successful live
acceptance cases, not a claim that all provider attempts passed. Three earlier bank-B UI runs
stopped with MODEL_PROVIDER_ERROR; their run summaries and evidence remain local. A neutral
provider request subsequently passed, followed by the successful fourth UI attempt.

Screenshot review confirmed the established navy/blue shell, goal/activity sidebar, large actual
managed application, separate capability/binding panels and zero-call Replay result. The full-page
Replay PNG captures a sticky header at its current scroll position; the live product's viewport
layout and five mobile routes passed. Only selected synthetic-demo frames were saved by the
acceptance script; production preview frames are transient. The synthetic input IDs are intentionally
visible in the requested demo captures. No configured credential, provider endpoint or raw model
response was included.

Implementation preserves CoreBank's known-profile POST search with an explicit exact read-only
route exception. Generic authorization otherwise requires the configured read-only origin/path;
page and model text cannot grant it. No significant dependency was added.

## Public submission delivery

Delivery status: **VERIFIED BEHAVIOR** on 2026-09-12. Local `main` was pushed to the public
[Capability Runner repository](https://github.com/ManoBharathi93/capability-runner). GitHub reports
`main` as the default branch and the repository as public. A credential-disabled `git ls-remote`
resolved the published branch, and anonymous HTTP requests to the repository page and raw README
both returned 200. The intended-public staged set was checked before the first push: local `.env`,
the assignment source, private provider notes, browser images, run data, caches, dependencies,
generated builds, and temporary reports were ignored; 229 staged text files had no matching
credential signature or workstation user path.

</details>
