# Implementation Plan

## Operating rules

Each milestone is separately authorized. Complete its focused tests, relevant regression checks, integration point, and `docs/progress.md` update, then stop. Parent milestones are not marked passed because one subdivision passed. Accepted architecture is not reopened during implementation; material public-contract, security, data, dependency, or scope changes require owner approval.

## P0: Architecture documentation

Status: completed documentation milestone. Acceptance did not establish implementation or behavioral verification.

## P1: Foundation and controlled interaction

### P1.0: Repository foundation

Structure, package setup, dependency rules, documentation, and smoke/architecture checks. No subsystem behavior. Complete and frozen.

### P1.1: Core contracts

Minimal requests, targets, observations, actions, session state, and results with validation and serialization tests. Add later contracts only with their consuming subsystem.

### P1.2: Evidence Recorder and redaction

Typed events, safe persistence, and synthetic-sensitive-value tests. Do not claim universal screenshot redaction.

### P1.3: Policy Guard

Trusted application/action/target policy and allowed, denied, unknown, and malformed cases. No browser execution.

### P1.4: Session Controller

Lifecycle, serialized dispatch, ownership, and generation checks. Test stale and non-owner actions. Full operator handoff remains P4.1.

### P1.5: Browser Surface Adapter and sample target

Build the synthetic member-servicing application. Implement supported observations, validated targeting, click/fill/read, and cleanup with local-browser integration tests.

### P1.6: Action Gateway integration

Connect policy, ownership, adapter, and evidence. Add only the coordinator/CLI wiring needed for a diagnostic. Prove one permitted and one rejected action through the real boundary.

## P2: Capability and deterministic replay

### P2.1: Capability definition, Validator, and Store

Implement the typed artifact language incrementally with immutable version handling, reference checks, and safe storage. Hand-authored artifacts remain development fixtures.

### P2.2: State Evaluator

Evaluate declared entity checks, outputs, known business outcomes, and unknown states without a model or browser operation.

### P2.3: Replay Engine

Implement parameter binding, deterministic steps/branches, bounded recovery, and structured results. Replay with model access absent and verify fresh application data.

## P3: Discovery

### P3.1: Model Client and provider adapters

Implement the normalized contract and separately contract-test OpenAI, Anthropic, and hosted Gemma. Record live status per provider/deployment.

### P3.2: Discovery Engine

Implement a bounded observe-decide-act loop. The model proposes; Action Gateway authorizes and performs.

### P3.3: Capability Builder and discovery-to-replay integration

Convert a verified discovery trace into a reusable artifact and replay it with another input. This closes the mandatory genuine discovery path.

## P4: Human intervention

### P4.1: Intervention Manager and Operator Interface

Implement same-session takeover, sanitized human-action capture, and validated return for discovery and replay.

### P4.2: Minimal Operator Console

Expose one local same-session operator page and thin HTTP API over P4.1. Provide bounded ephemeral
browser views, currently visible trusted semantic fill/click controls, explicit return, and stop.
Do not continue Discovery or Replay after handback.

### P4.3: Automatic continuation

Implemented and verified for Replay `APPROVAL_REQUIRED`: safe approval-only checkpoints,
same-session fresh validation, new-generation restoration, exactly-once continuation through the
existing Replay loop, and terminal success without repeated prior actions. Discovery continuation
and generalized failure recovery are not implemented.

## P5: Product and submission

### P5.1: Final assignment compliance and submission-readiness audit

Status: completed documentation audit. The repository was evaluated against `Assignment.md`, the
system design was condensed into a reviewer-facing narrative, and the executive verdict was
**NOT READY**. No product feature was implemented. See `docs/submission/`.

### P5.2: Reproducibility and demo entry point

Status: completed and verified. The `capability-runner demo` command group now provides genuine
discovery/build/store/fresh model-free replay, same-session intervention/resume through the existing
operator HTTP API, and one exceptional business-outcome replay. Runtime output is written beneath
`var/demo-runs/`; no curated submission evidence was created. The frozen P1-P4 engines were reused.

### P5.3: Documentation, evidence, and submission packaging

Status: completed locally with one external delivery action. The root README contains exact setup
and demo commands, `REPORT.md` and genuine sanitized evidence are present, and local packaging,
privacy, portability, and link checks pass. This workspace has no Git metadata or public URL, so
public-repository contents and anonymous access remain **EXTERNAL-MANUAL**. `REPORT.md` uses exactly
these headings:

1. Architecture
2. Artifact schema
3. Determinism & error handling
4. Heterogeneity & multi-tenant
5. Escalation & handoff
6. Safety
7. Cuts

### P5.4: Optional polish

Separately authorize any recording, React product frontend, capability catalog, stability report,
second adapter, tenant-variant demonstration, or visual refinement. Optional polish must not delay
the mandatory submission package.

### P5.4a: Evidence observability

Status: implemented under separate narrow authorization. Discovery and Replay expose optional
passive evidence-writer seams, Replay records start/step/terminal/resume lifecycle, and the
continuation coordinator records bounded capability/step/current-state intervention context.
Reviewer composition uses the existing Evidence Recorder. Runtime decisions, policy, session
ownership, model-free Replay, and protected invocation-value handling are unchanged.

### P5.4a.1: Provider-backed Discovery evidence

Status: completed under separate narrow authorization. The existing neutral live ModelClient smoke
and public reviewer through-line ran against configured Gemma. The successful runtime summary,
capability, and evidence JSONL replaced the curated through-line byte-for-byte after lifecycle,
provenance, parse, and privacy checks. No source, tests, contracts, or runtime semantics changed.

### P5.4b: Product frontend from current references

Status: implemented under separate owner authorization. The React/TypeScript/Vite client and thin
demo-owned HTTP composition implement the complete four-image current reference set using validated
local artifacts and the existing Discovery, model-free Replay, and same-session Intervention paths.
Implementation captures and a fidelity report are recorded under `docs/references/ui/implemented/`
and `docs/ui/visual-fidelity-report.md`. Teach is visual-only; no P6 media behavior was added.

## P6: Optional teaching extension

Requires passing core acceptance and explicit owner authorization. Add the Teams-like chat/call, voice, and screen teaching path by reusing the accepted capability and execution core.

## Stop gate

P5.3 local packaging and the separately authorized P5.4a, P5.4a.1, and P5.4b slices are complete.
P1-P4 and P5.2 remain frozen. Do not begin additional P5.4 work or P6 without explicit owner
authorization. Public repository creation and publication require owner action.

## Owner-authorized Generic Discovery milestone (2026-09-12)

The explicit GENERIC DISCOVERY + LIVE WORKSPACE + EVALUATION request supersedes the preceding
stop gate for this milestone. Preserve trusted-profile operation and add bounded profile-less
browser observations, current-generation refs, deterministic generated packages, fresh model-free
Replay, live same-session UI and separate scripted/live evaluations. See
[subsystem record](subsystems/generic-discovery.md) and [progress](progress.md) for actual evidence.
No Teach/voice/screenshare or external publication is authorized by this milestone.

Status: implemented and scoped verification passed. Both real-provider browser UI acceptances,
different-input zero-model Replay, normal evaluations and final gates are recorded in
`docs/progress.md`. Stop here; additional authoring modes or broader application scope require
separate authorization.
