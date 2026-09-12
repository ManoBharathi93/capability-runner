# Repository Guidance

The architecture in `docs/architecture.md` and accepted entries in `docs/adr/README.md` are owner-approved baseline decisions. Treat them as constraints, not design prompts. Acceptance does not imply implementation or verification.

Before implementation work, read `docs/requirements.md`, `docs/repository-map.md`, `docs/implementation-plan.md`, `docs/progress.md`, `docs/providers.md`, `docs/ui-spec.md`, and the relevant subsystem record. Follow `.agents/skills/capability-runner-engineering/SKILL.md` for milestone execution and evidence updates.

Use exactly these status labels:

- **ACCEPTED BASELINE** for owner-approved direction.
- **PROPOSED IMPLEMENTATION DETAIL** for a new unresolved choice.
- **VERIFIED BEHAVIOR** only when a completed test or experiment and its evidence are recorded in `docs/progress.md`.

Do not replace established component names or responsibilities, add services/frameworks/layers for appearance, or build future teaching components during the required core milestones. Replay must remain independent of Model Client; all surface actions must pass through Action Gateway.

For a material open detail, record constraints, alternatives, recommendation, downside, and validation test. Obtain owner approval before changing a public contract, security or data handling, significant dependencies, or scope. For a concrete contradiction or failed baseline assumption, record evidence and the smallest necessary change, then pause affected work for review rather than silently redesigning.

Honor the current authorization in `docs/progress.md`. P1.0 permits repository/package foundation, dependency-boundary checks, and documentation only; do not implement P1.1 contracts or later subsystems. Label unimplemented examples illustrative and record actual checks separately from design acceptance.

For later milestones, load only the documents and source files directly relevant to the current subsystem and rerun only the affected checks. Do not repeat completed foundation audits when their evidence already exists in `docs/progress.md`.