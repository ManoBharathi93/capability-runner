# Submission readiness report

## Verdict

**READY** against the assignment's 30 mandatory requirements.

The source is published at [github.com/ManoBharathi93/capability-runner](https://github.com/ManoBharathi93/capability-runner) on `main`. The repository is public, and anonymous access to both the repository page and raw README returned HTTP 200 after publication. The assignment audit is recorded in [requirement-traceability.md](requirement-traceability.md).

## Implemented and verified

The repository contains a complete Discovery-to-Replay vertical slice against real synthetic banking UIs. Discovery accepts natural-language goals, uses a configured model in a bounded observe-decide-act loop, and sends actions through the shared Action Gateway. Successful verified traces compile into typed, versioned capability JSON with a separate application profile. Fresh Replay loads that package, accepts different inputs, checks current state and identity, and returns typed outputs without a Model Client dependency.

The React product provides Discover, Capability Library, Runs, Human Interventions, Evidence, and a clearly disabled Teach route. The Discovery workspace shows the actual managed browser session, a structured timeline, the capability and binding, and a different-input Replay form. A second structurally different application, LegacyBank B, has completed real-provider profile-less Discovery and fresh model-free Replay. This is evidence for bounded generic browser discovery, not universal website support or reuse of one identical capability across tenants.

The same-session handoff path pauses before an approval-required action, transfers ownership to an operator, routes typed operator controls through policy, re-observes state at handback, advances the generation, and resumes once without repeating the blocked action. The local operator UI is functional but unauthenticated and process-local.

Curated evidence under `evidence/` includes a real provider-backed Discovery and fresh Replay through-line, a generated capability, a model-free business outcome, an intervention run, and bounded terminal failure state. The records omit raw prompts, model payloads, selectors, raw DOM, credentials, private endpoints, and invocation values.

The latest recorded verification is:

- 371 ordinary Python tests passed; 8 opt-in live tests were deselected by default;
- 7 frontend tests passed;
- TypeScript typecheck and the Vite production build passed;
- Ruff and Pyright passed;
- the Python lock consistency check passed;
- the deterministic banking evaluation passed 13 of 13 cases with nine matching fresh Replay results, three generated profiles, zero false successes, zero wrong-entity successes, zero unsafe actions, and zero Replay model calls.

The exact commands and dated evidence are in [progress.md](../progress.md). Real-provider successes and failures are recorded separately; no reliability percentage is inferred from a small number of attempts.

## Reviewer entry points

Use the root [README](../../README.md) for setup and the shortest reproducible commands. Use [manual-test-guide.md](manual-test-guide.md) for product inputs, expected outputs, negative cases, CLI checks, the 13-case evaluation, and focused browser safety tests. Use [demo-walkthrough.md](demo-walkthrough.md) for the eight-to-ten-minute video script. The root [REPORT](../../REPORT.md) explains the architectural decisions and trade-offs in the seven headings required by the assignment.

## Remaining limitations

The implemented browser scope is allowlisted and read-only. It supports visible ordinary HTML controls, bounded same-origin frames, and current input/output extraction; unsupported or ambiguous controls fail closed. Sessions and intervention ownership live in one process. Provider availability and decision quality can affect Discovery, while Replay remains provider-independent. Generated packages prove observed interactions and declared outcomes, not unobserved business outcomes.

The product does not include production authentication, durable browser-session recovery, distributed scheduling, encrypted artifact storage, universal screenshot or semantic PII redaction, a desktop adapter, or automated profile repair. Voice, screen sharing, and Teach are not implemented. The evaluation harness is regression evidence rather than a persisted draft-to-approved qualification workflow. Reuse of one byte-identical capability across two tenant profiles has not yet been demonstrated.

These limitations do not contradict the mandatory assignment scope, but they define where a production banking system would need more work before handling regulated data or unattended side effects.
