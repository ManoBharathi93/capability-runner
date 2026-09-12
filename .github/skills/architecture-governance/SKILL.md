---
name: architecture-governance
description: "Use when implementing or documenting capability-runner architecture, changing component boundaries, resolving open implementation details, recording experiments, or updating architecture/progress status."
---

# Architecture Governance

Apply this workflow whenever work touches architecture, public contracts, safety, data handling, providers, live-session control, capability definitions, replay, evidence, or phase scope.

## Sources of truth

1. Read `docs/architecture.md` for accepted components, responsibilities, dependency flows, and phase gate.
2. Read `docs/adr/README.md` for rationale, trade-offs, assumptions, proposed details, validation tests, and revisit conditions.
3. Read `docs/progress.md` before describing implementation or verification status.
4. Read `Assignment.md` for unchanged deliverable and evaluation requirements.

If documents conflict, do not silently choose a new architecture. Record the contradiction and ask the owner to resolve it.

## Classify before acting

Classify the subject with exactly one status:

- **ACCEPTED BASELINE:** implement or document it within the authorized milestone. Do not ask the owner to choose the architecture again.
- **PROPOSED IMPLEMENTATION DETAIL:** the baseline requires a choice but does not prescribe it. Separate recommendation from approval.
- **VERIFIED BEHAVIOR:** use only after a named test or experiment completed and evidence is linked in `docs/progress.md`.

Never use "accepted," "implemented," and "verified" as synonyms.

## Apply an accepted decision

1. Identify the owning component and dependency boundary in `docs/architecture.md`.
2. Find the corresponding ADR constraints, disadvantages, failure modes, and assumptions.
3. Keep the change inside the authorized milestone and the smallest responsible module.
4. Preserve established component names and responsibilities.
5. Run the ADR's cheapest relevant assumption test before broadening work.
6. Record implementation status separately from test status in `docs/progress.md`.
7. Link sanitized evidence before changing a claim to **VERIFIED BEHAVIOR**.

Do not add a service, framework, abstraction layer, or future component solely to make the design appear more sophisticated. Do not create the future teaching path while the required assignment execution path is incomplete.

## Resolve an open detail

For a non-trivial unresolved choice, add or update a **PROPOSED IMPLEMENTATION DETAIL** with:

- the constraint and affected component/contract;
- credible alternatives;
- a recommendation and why it fits this milestone;
- its downside and likely failure mode;
- a discriminating test or experiment;
- the approval or revisit trigger.

Proceed without repeated approval for trivial private implementation details. Request owner approval before changing public capability/result/control contracts, security or data handling, significant dependencies, or scope.

## Handle contrary evidence

If a test exposes a concrete conflict with the accepted baseline:

1. Preserve the failing output as sanitized evidence.
2. Mark the behavior failed or blocked in `docs/progress.md`; do not rewrite history.
3. Add the contradiction to the decision register.
4. Describe the smallest necessary change and its effects on boundaries, contracts, safety, and scope.
5. Pause only the affected work and request owner review.

An alternative being plausible is not contrary evidence. A reproducible failure against a stated assumption is.

## Update evidence and progress

For each completed experiment, record:

- date and exact test/command or manual procedure;
- decision/assumption tested;
- environment and relevant versions without secrets;
- expected and observed behavior;
- pass, fail, or inconclusive result;
- sanitized evidence path;
- consequence for the decision or proposed detail.

Implementation status uses `not started`, `in progress`, `implemented`, or `blocked`. Verification status uses `not run`, `passed`, `failed`, or `inconclusive`. A component can be implemented and still unverified.

## Phase restriction

Read `docs/progress.md` for the current authorization. P1.0 permits repository/package foundation, static dependency checks, smoke tests, and documentation; it does not permit P1.1 contracts or later subsystem behavior. Never invoke model providers, automate a browser, or generate fake `/evidence/` results in P1.0. Label unimplemented examples illustrative and stop at the recorded gate.