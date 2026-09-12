---
name: capability-runner-engineering
description: "Use when implementing, testing, or documenting a Capability Runner milestone while preserving accepted architecture, dependency boundaries, safety constraints, evidence status, and phase gates."
---

# Capability Runner Engineering

## Read before changing code

1. Read `AGENTS.md` and `.github/copilot-instructions.md`.
2. Read `docs/requirements.md`, `docs/architecture.md`, and accepted ADRs.
3. Read `docs/repository-map.md` for ownership and dependency rules.
4. Read `docs/providers.md` and `docs/ui-spec.md` when the milestone touches those surfaces.
5. Read `docs/implementation-plan.md` and `docs/progress.md` to identify the one authorized milestone.
6. Use `docs/subsystems/_template.md` for the subsystem record.
7. Treat `docs/references/` as visual concepts, not implementation evidence.

If a required source is missing or conflicts with the accepted baseline, report it. Do not invent prior approval or progress.

## Execute one authorized subsystem

1. Map existing files to the accepted owner before creating anything; reuse compatible work.
2. State the local hypothesis, owning path, and cheapest falsifying check.
3. Document the subsystem's input/output contract, state, dependencies, alternatives, costs, failure modes, and boundary tests before implementation.
4. Implement the smallest end-to-end behavior authorized by the milestone. Do not create placeholders for later components.
5. Run the focused test immediately after the first substantive edit, then relevant regression, lint, and type checks.
6. Integrate with already-built dependencies where the milestone requires it.
7. Update `docs/progress.md` with implementation and verification as separate facts.
8. Stop before the next subsystem and provide its prompt without executing it.

## Preserve boundaries

- Contracts have no browser, filesystem, provider, or orchestration behavior.
- Run Coordinator manages lifecycle, not individual UI decisions.
- Discovery may use Model Client, Action Gateway, and State Evaluator, never Playwright directly.
- Replay has no Model Client, provider adapter/SDK, or frontend dependency.
- State Evaluator is non-LLM and does not operate a browser.
- All discovery, replay, and operator surface actions pass through Action Gateway.
- Gateway/session code uses the Surface Adapter interface; concrete composition belongs in `bootstrap.py`.
- Playwright live handles remain in `browser_surface_adapter.py`.
- Provider wire formats and SDK objects remain in their corresponding provider adapter.
- Evidence accepts typed events through a narrow sink and does not import engines to scrape state.
- Production runner code never imports `demo_app` or test fixtures.
- Package initializers remain side-effect free.
- The frontend renders backend state and never becomes another workflow engine.

Static architecture tests are guardrails only. They do not prove model-free runtime execution, authorization, privacy, redaction, or safe browser behavior.

## Status and decisions

Use exactly:

- **ACCEPTED BASELINE** for owner-approved architecture/product direction.
- **PROPOSED IMPLEMENTATION DETAIL** for unresolved choices.
- **VERIFIED BEHAVIOR** only for completed tests or experiments recorded with evidence in `docs/progress.md`.

Resolve small reversible details inside the authorized subsystem. Before changing a public contract, relaxing safety, adding a significant dependency, changing data destinations, or expanding scope, record constraints, alternatives, recommendation, downside, and test, then request owner approval.

If evidence contradicts an accepted assumption, preserve sanitized failure evidence, record the contradiction and smallest necessary change, and pause the affected work. Do not silently redesign.

## Current gate

P1.0 is repository foundation only. Package markers, configuration, dependency rules, documentation, and genuine smoke/static checks are allowed. Core Pydantic contracts, evidence behavior, policy, sessions, browser integration, gateway wiring, providers, engines, web application code, demo application code, and teaching are not authorized in P1.0.