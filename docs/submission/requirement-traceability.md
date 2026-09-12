# Assignment Requirement Traceability

## Audit basis

This P5.1 audit evaluates the repository against the original `Assignment.md`, not against the
internal milestone plan. P1-P4 remain frozen. No missing product behavior was implemented during
this audit.

Statuses mean:

- **PASS**: implementation exists and a completed test is recorded in `docs/progress.md`.
- **PARTIAL**: some required behavior or proof exists, but the assignment requirement is not fully
  satisfied or is not reproducible from the submission surface.
- **MISSING**: the required implementation, artifact, or deliverable is absent or cannot be
  verified from this workspace.
- **OUT_OF_SCOPE_OPTIONAL**: an assignment stretch goal, not part of the mandatory count.

The evidence column distinguishes executable tests from submission artifacts. A passing test that
writes only to pytest temporary storage is not a curated `/evidence/` deliverable.

## Mandatory matrix

| ID | Source | Assignment requirement | Implementation owner | Automated evidence / demo path | Status | Audit finding |
| --- | --- | --- | --- | --- | --- | --- |
| D-01 | §3.1 | Accept a natural-language goal and target application | `contracts/requests.py`, `discovery/discovery_engine.py` | `tests/unit/discovery/test_discovery_engine.py`; live browser test below | **PASS** | Typed request and profile entry point reach Discovery. |
| D-02 | §3.1 | Run a bounded LLM observe-decide-act loop | `discovery/discovery_engine.py`, `discovery/model_client.py` | `uv run pytest tests/unit/discovery/test_discovery_engine.py -q` and the live P3 test | **PASS** | Turn, action, timeout, invalid-response, and no-progress stops are enforced. |
| D-03 | §3.1 | Drive a real UI and read its state | `surfaces/browser_surface_adapter.py` | `uv run pytest tests/integration/surfaces/test_browser_surface_adapter.py -q` | **PASS** | Real local Flask UI and Chromium exercise fill, click, frame, row, observation, and cleanup behavior. |
| A-01 | §3.2 | Artifact contains ordered steps/actions | `contracts/capabilities.py`, `capabilities/capability_builder.py` | `uv run pytest tests/unit/capabilities tests/integration/capabilities -q` | **PASS** | Steps are typed, ordered, and compiled from a verified trace. |
| A-02 | §3.2 | Artifact identifies controls robustly | `contracts/surfaces.py`, trusted `ApplicationProfile` bindings | `uv run pytest tests/unit/contracts/test_surface_contracts.py tests/integration/surfaces/test_browser_surface_adapter.py -q` | **PASS** | Semantic targets are separated from ordered role/label/text/CSS, frame, and row bindings. |
| A-03 | §3.2 | Artifact declares typed inputs | `contracts/capabilities.py` | `uv run pytest tests/unit/contracts/test_capability_contracts.py -q` | **PASS** | Inputs include type, requiredness, sensitivity, and optional validation constraints. |
| A-04 | §3.2 | Artifact declares typed outputs and extraction | `contracts/capabilities.py`, `replay/state_evaluator.py` | `uv run pytest tests/integration/replay/test_replay_engine_browser.py::test_real_browser_replay_returns_parameterized_success -q` | **PASS** | Replay returns parsed balance and currency outputs. |
| A-05 | §3.2 | Artifact declares success/checkpoint conditions | `contracts/capabilities.py`, `replay/state_evaluator.py` | `uv run pytest tests/unit/replay/test_state_evaluator.py -q` | **PASS** | Explicit terminal conditions are evaluated without a model. |
| A-06 | §3.2 | Artifact is typed, serializable, versioned, and reviewable | `contracts/capabilities.py`, `capabilities/capability_validator.py`, `capabilities/capability_store.py` | `uv run pytest tests/unit/capabilities tests/integration/capabilities -q` | **PASS** | Immutable schema-v1 JSON and semantic versions are validated before storage. |
| R-01 | §3.3 | Replay a saved artifact without LLM decisions | `replay/replay_engine.py` | `uv run pytest tests/integration/replay/test_replay_engine_browser.py::test_real_browser_replay_succeeds_without_model_environment -q` | **PASS** | Replay has no Model Client/provider dependency and succeeds with model configuration absent. |
| R-02 | §3.3 | Use stable targeting, verify success, return outputs | Replay, State Evaluator, Action Gateway, Surface Adapter | `uv run pytest tests/integration/replay/test_replay_engine_browser.py -q` | **PASS** | Fresh-browser replay resolves trusted bindings, verifies terminal state, and extracts typed outputs. |
| R-03 | §3.3 | Detect runtime errors and exceptional states deliberately | Replay and State Evaluator | Same seven-case browser replay module | **PASS** | Not-found, restricted, expired, slow-within-bound, and slow-beyond-bound scenarios are covered. |
| R-04 | §3.3 | Separate business outcomes, recoverable conditions, and hard failures | `contracts/replay.py`, `replay/state_evaluator.py`, `replay/replay_engine.py` | `uv run pytest tests/unit/replay tests/integration/replay -q` | **PASS** | Terminal result is success, business outcome, or failure; bounded retries remain internal recovery. |
| R-05 | §3.3 | Return clear debuggable structured replay results | `contracts/replay.py` | `uv run pytest tests/unit/replay tests/integration/replay -q` | **PASS** | Result includes run, outcome, reason, failed step, summary, attempts, outputs, and safe continuation checkpoint where applicable. |
| S-01 | §3.4 | Enforce configurable allowlists and deny unknown actions | `interaction/policy_guard.py`, `interaction/action_gateway.py` | `uv run pytest tests/unit/interaction/test_policy_guard.py tests/unit/interaction/test_action_gateway.py -q` | **PASS** | Trusted application/profile, action, semantic target, and normalized navigation rules are deny-by-default. |
| S-02 | §3.4 | Treat risky/irreversible actions conservatively | Policy Guard, Replay continuation, Intervention Manager | `uv run pytest tests/unit/replay/test_replay_engine.py tests/unit/application/test_run_coordinator.py -q` | **PASS** | `REQUIRE_APPROVAL` blocks dispatch; only a proven `NOT_EXECUTED` action receives a resumable checkpoint. |
| S-03 | §3.4, §9 | Do not persist secrets or raw sensitive values | Capability Builder, `evidence/redaction.py`, Evidence Recorder | `uv run pytest tests/unit/evidence tests/unit/capabilities -q` | **PASS** | Artifacts store parameter references; evidence redacts `SecretStr`, sensitive keys, and explicit values before write. This is exact-value/key redaction, not universal PII detection. |
| E-01 | §3.5 | Structured log of what the agent did and why | Evidence Recorder, Discovery, Replay, gateways, and reviewer demo runtime | Curated through-line, exception, intervention, and failure JSONL under `evidence/` | **PASS** | The refreshed genuine Gemma/Chromium through-line records Discovery start, observations, five bounded semantic decisions with fingerprints, authorized actions, completion, capability build/validate/store/load, and complete fresh Replay lifecycle. It persists no raw prompt, response, rationale, provider payload, endpoint, credential, selector, goal, runtime input map, or sensitive invocation value. |
| E-02 | §3.5 | At least one richer failure signal | Browser Surface Adapter and reviewer demo runtime | Existing `session_expired` mode through reviewer Replay composition; P5.2 record in `docs/progress.md` | **PASS** | A genuine terminal Replay failure invokes bounded surface capture and persists sanitized current-state text as a structured error event. Operator-page screenshots remain ephemeral and are not claimed as failure evidence. |
| H-01 | §3.6 | Detect a blocked state and route an intervention | Replay, coordinator, Intervention Manager | `uv run pytest tests/unit/application/test_run_coordinator.py tests/unit/intervention -q` | **PASS** | Approval-blocked replay raises one bounded intervention; uncertain effects are not auto-resumed. |
| H-02 | §3.6 | Carry capability/goal, step, current state, and stop reason | `contracts/intervention.py`, coordinator registry, operator console | Curated `evidence/intervention/` run plus P4.1-P4.3 and P5.4a tests | **PASS** | The persisted sanitized context identifies the capability/version, blocked step/index and semantic target, `blocked_before_dispatch` state, `APPROVAL_REQUIRED` stop reason, and runtime input names without values; the correlated log proves same-session handoff and resume. Protected invocation values remain in memory only. |
| H-03 | §3.6 | Let a human control the same live session | Session Controller, Intervention Manager, Operator Action Gateway, operator HTTP page | `uv run pytest tests/integration/intervention/test_human_handoff_browser.py tests/integration/interfaces/test_operator_console_browser.py -q` | **PASS** | Real Chromium acceptance preserves one opaque surface session across transfer. |
| H-04 | §3.6 | Preserve evidence and record human actions | Operator Action Gateway, Evidence Recorder | `uv run pytest tests/unit/intervention tests/integration/intervention -q` | **PASS** | Human fill/click actions traverse policy and are recorded as operator-action intervention events. Production authentication and explicit operator identity in persisted events are not claimed. |
| H-05 | §3.6 | Hand control back and resume safely with known ownership | Session Controller, continuation coordinator, Replay Engine | `uv run pytest tests/end_to_end/test_replay_intervention_resume.py -q` | **PASS** | Fresh state is validated, generation advances, stale actions fail, and Replay resumes exactly once without repeating prior actions. |
| G-01 | §3.7 | Credible surface-abstraction path to legacy web/desktop | Surface contracts/port and architecture docs | `uv run pytest tests/architecture/test_dependency_boundaries.py tests/unit/surfaces/test_surface_adapter_contract.py -q` | **PASS** | Replay and artifact semantics are Playwright-free; a second adapter is intentionally design-only. |
| G-02 | §3.7 | Credible multi-tenant reuse, specialization, and drift design | `ApplicationRequirement`, `ApplicationProfile`, `docs/architecture.md` | Review `docs/submission/system-design.md`; implementation not required by assignment | **PASS** | Base vendor capability plus variant profiles, narrow overrides, preflight/drift detection, quarantine, and fail-closed behavior are described. No multi-tenant runtime claim is made. |
| L-01 | §6.1 | Root README explains setup, configuration, offline mode, and exact discovery then replay demo | `README.md` | P5.2 command runs; P5.3 README/link inspection | **PASS** | The root README documents fresh setup, explicit Chromium installation, provider variables and no-fallback behavior, exact live and model-free commands, expected results, output locations, checks, and limits. |
| L-02 | §6.2 | Root `REPORT.md` uses the seven required headings | Repository root | P5.3 exact-heading check | **PASS** | `REPORT.md` exists and contains exactly the seven required second-level headings in assignment order. |
| L-03 | §4, §5, §6.3 | `/evidence/` contains a generated artifact plus discovery and replay logs | `evidence/` | P5.3 provenance, hash, parse, path, and privacy checks | **PASS** | Byte-identical files from genuine runs include the generated artifact, combined Discovery/fresh-Replay log and summary, a model-free business outcome, and bounded terminal-failure surface evidence. |
| L-04 | §6.1, §11 | Source is delivered in a public Git repository | Submission transport | Public repository plus anonymous repository and raw README access checks | **PASS** | Source is on public `main` at [github.com/ManoBharathi93/capability-runner](https://github.com/ManoBharathi93/capability-runner); both anonymous checks returned HTTP 200 after publication. |

## Count and verdict

Mandatory rows: **30**.

- **PASS:** 30
- **PARTIAL:** 0
- **MISSING:** 0

The submission package is **READY** against the mandatory matrix. All 30 mandatory rows have
implementation or delivery evidence. Optional product hardening and qualification work remain
clearly separated below.

## Optional scope

The assignment's agent-facing capability catalog, code generation, confidence/approval lifecycle,
bounded LLM fallback, cross-tenant runtime demonstration, and multi-run stability report are
**OUT_OF_SCOPE_OPTIONAL**. The implemented React product frontend and capability catalog improve
reviewability, while the remaining optional items must not obscure the required
discovery-to-replay story.

## Proof boundaries

- The genuine provider-backed P3 live test is recorded as previously passed in
  `docs/progress.md`; it was not rerun during P5.1.
- The current collection has 379 cases: 371 ordinary cases and 8 opt-in live cases.
- Default pytest excludes `live`, so ordinary tests do not call external model providers. Browser
  integration tests use local Chromium and a loopback Flask server.
- `playwright` installation does not install Chromium automatically. The root README includes the
  required explicit browser-install command.
- `.env.example` contains all eight provider variable names expected by provider documentation;
  values are empty/placeholders. This proves template shape, not credential validity.
- The latest completed full gates are 371 passed with 8 live cases deselected; 7 frontend tests,
  TypeScript typecheck, production build, Ruff, Pyright, and lock consistency passed.
- P5.4a.1 changed curated evidence and documentation only. Its focused evidence regression passed
  17 tests; all three refreshed through-line files parse, match their runtime sources byte-for-byte,
  and contain zero prohibited privacy matches.
- P5.3 changed documentation and copied runtime evidence only; it did not alter source, tests,
  package configuration, or the lock. Fresh P5.3 checks validated the exact report headings, all
  local Markdown links, required file existence, JSON/JSONL parsing, summary-relative paths,
  byte-identical evidence provenance, model-free exception/intervention commands, and intended-public
  privacy/portability patterns.
