# Architecture Governance

Follow the accepted baseline in `docs/architecture.md` and `docs/adr/README.md`. Do not reopen accepted decisions or present alternatives as undecided architecture. Preserve established component names, responsibilities, dependency boundaries, assignment requirements, safety restrictions, provider requirements, UI requirements, and phase gates.

Before changing implementation, read `docs/requirements.md`, `docs/repository-map.md`, `docs/implementation-plan.md`, `docs/progress.md`, `docs/providers.md`, `docs/ui-spec.md`, and `.agents/skills/capability-runner-engineering/SKILL.md`.

Keep status precise: **ACCEPTED BASELINE** is approved direction, **PROPOSED IMPLEMENTATION DETAIL** is unresolved, and **VERIFIED BEHAVIOR** requires a completed test with evidence recorded in `docs/progress.md`. Never infer implementation or verification from acceptance.

Resolve trivial details locally. For material contract, security, data-handling, dependency, or scope choices, document the constraint, alternatives, recommendation, downside, and test, then request owner approval. If evidence contradicts the baseline, document the failure and smallest necessary change and pause affected work.

The current authorization is P1.0 repository foundation only. Do not implement P1.1 or later behavior. Required assignment execution precedes optional voice-and-screen teaching features.