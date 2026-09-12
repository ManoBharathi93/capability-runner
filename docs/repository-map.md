# Repository Map

## Status

The directory layout maps the **ACCEPTED BASELINE** modular-monolith responsibilities into one Python package and one deferred React client. P1.0 creates package boundaries and tests, not subsystem implementations. Filenames marked "planned" below do not exist until their milestone needs them.

## Layer-to-directory ownership

| Architectural layer | Code location | Responsibility | Owned state | Allowed dependencies | Forbidden dependencies | Primary tests | Milestone |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Shared contracts | `src/capability_runner/contracts/` | Pydantic agreements shared across core modules. | Immutable values and validated request/result data; no runtime resources. | Standard library and approved validation/type libraries. | Other production subsystems, browser/filesystem operations, provider calls, vendor SDKs, orchestration. | `tests/unit/contracts/` | P1.1 onward, added with consumers. |
| Application | `src/capability_runner/application/` | Coordinate run creation, lifecycle, routing, stopping, and result assembly. | Run coordination state through owned collaborators. | Contracts and narrow interfaces of discovery, replay, intervention, session, and evidence components. | Individual UI-action selection, raw browser handles, provider wire formats, frontend code. | `tests/unit/application/`, integration tests | Begins P1.6; expands through P4.1. |
| Discovery | `src/capability_runner/discovery/` | Bounded LLM-driven observation, decision, and action proposal. | Discovery-loop progress, not provider or browser handles. | Contracts, provider-neutral Model Client, Action Gateway, State Evaluator. | Direct Playwright, direct surface dispatch, Capability Store publication, provider SDKs outside `providers/`. | `tests/unit/discovery/`, `tests/integration/discovery/`, `tests/live/` | P3.2. |
| Provider adapters | `src/capability_runner/discovery/providers/` | Translate normalized Model Client requests/responses for OpenAI, Anthropic, and hosted Gemma. | Adapter-local clients and deployment capability metadata. | Provider-neutral contracts and the adapter's own SDK/transport. | Vendor objects returned into core, replay, direct browser control. | `tests/unit/discovery/providers/`, opt-in `tests/live/` | P3.1. |
| Capabilities | `src/capability_runner/capabilities/` | Build, structurally/semantically validate, and store reusable definitions. | Versioned capability documents and local publication metadata. | Contracts, approved filesystem abstraction for Store, policy compatibility checks. | Browser execution during structural validation, raw transcripts, arbitrary generated code. | `tests/unit/capabilities/`, `tests/integration/capabilities/` | P2.1; Builder integration P3.3. |
| Replay | `src/capability_runner/replay/` | Interpret saved instructions and evaluate declared conditions deterministically. | Per-run interpreter progress and extracted outputs. | Contracts, Action Gateway and intervention interfaces, deterministic State Evaluator. | Discovery, Model Client, provider adapters/SDKs, frontend modules, direct Playwright. | `tests/unit/replay/`, `tests/integration/replay/`, `tests/end_to_end/` | P2.2-P2.3. |
| Controlled interaction | `src/capability_runner/interaction/` | Authorize and serialize automated/human interaction through policy and ownership checks. | Policy decisions, session ownership, control generation, dispatch coordination. | Contracts, Surface Adapter interface, narrow evidence sink. | Inventing workflows, model decisions, direct provider calls; concrete adapter creation outside bootstrap. | `tests/unit/interaction/`, `tests/integration/interaction/` | P1.3-P1.4 and P1.6. |
| Surfaces | `src/capability_runner/surfaces/` | Translate approved actions into concrete surface observations and operations. | Live surface handles and adapter-specific target-resolution state. | Contracts and implementation-specific tooling inside concrete adapters. | Banking/business decisions, model calls, capability storage, policy bypass. | `tests/unit/surfaces/`, `tests/integration/surfaces/` | P1.5. |
| Intervention | `src/capability_runner/intervention/` | Route human assistance and coordinate explicit same-session ownership transfer. | Intervention request lifecycle; Session Controller remains ownership authority. | Contracts, Session Controller and narrow evidence/application interfaces. | Direct browser dispatch, ownership bypass, replacement sessions presented as handoff. | `tests/unit/intervention/`, `tests/integration/intervention/`, `tests/end_to_end/` | P4.1. |
| Evidence | `src/capability_runner/evidence/` | Sanitize and persist supported typed events and approved attachments. | Local evidence streams and redaction policy application. | Contracts, standard filesystem APIs, narrow event-sink contracts. | Engine imports to scrape state, post-hoc business decisions, raw secret persistence. | `tests/unit/evidence/`, `tests/integration/evidence/` | P1.2. |
| Interfaces | `src/capability_runner/interfaces/` | Convert CLI, HTTP, and operator input into application requests and render responses. | Transport/UI session state only where required. | Contracts and application-facing services. | Duplicate workflow engines, policy reimplementation, direct provider/browser access. | `tests/unit/interfaces/`, `tests/integration/interfaces/` | HTTP/operator P4.1-P4.3; reproducibility command P5.2. |
| Product frontend | `web/` | Render backend state and collect user/operator input. | Client presentation state; no authoritative run/control state. | Thin web API and frontend libraries selected only if P5.4 is authorized. | Provider secrets, independent Playwright/browser automation, duplicated execution logic. | Frontend tests under `web/` when implemented; end-to-end tests in `tests/end_to_end/`. | Optional P5.4. |
| Synthetic target | `demo_app/` | Provide the UI being operated, including controlled runtime outcomes. | Synthetic member/application data owned by the demo app. | Its own later-selected web stack and synthetic fixtures. | Imports from production runner; runner imports of demo fixtures/database. | Demo unit tests plus runner integration/end-to-end tests. | P1.5. |

## Supporting locations

| Location | Purpose | Boundary |
| --- | --- | --- |
| `config/profiles/` | Nonsecret trusted application/profile configuration. | No credentials or private hostnames. |
| `config/policies/` | Nonsecret execution policy definitions. | Policy data, not policy implementation. |
| `tests/architecture/` | Static dependency and repository-layout checks. | Useful guardrails; not runtime safety proof. |
| `tests/smoke/` | Package/import/configuration sanity checks. | Not discovery, replay, policy, or provider verification. |
| `tests/unit/` | Isolated behavior tests added with each subsystem. | Test doubles cannot establish live integration. |
| `tests/integration/` | Collaborator and local resource integration. | Provider/browser claims need their explicit environments. |
| `tests/end_to_end/` | Required full-path scenarios. | Added only when the path exists. |
| `tests/live/` | Explicitly opt-in model/provider tests. | Never run implicitly or require checked-in secrets. |
| `tests/fixtures/` | Test-only examples, including explicitly hand-authored development artifacts. | A fixture is not a generated capability or submission evidence. |
| `scripts/` | Small genuine developer utilities. | No hidden application or orchestration layer. |
| `var/` | Ignored local runtime capabilities, runs, evidence, browser state, and future teaching temporary data. | Never curated submission evidence; teaching storage is P6-only. |

## Similar names with different ownership

- `src/capability_runner/capabilities/` is implementation code for building, validating, and storing definitions.
- `var/capabilities/` is ignored local runtime capability data.
- `tests/fixtures/` contains test-only examples, including explicitly hand-authored development artifacts.
- `evidence/` contains selected, sanitized evidence from actual execution for the submission.
- `docs/references/ui/current/` contains generated visual concepts, not execution evidence.
  `docs/references/ui/implemented/` contains selected actual product captures linked to the
  corresponding verification records in `docs/progress.md`.

## Planned production files

P1.0 creates package markers only. The following names reserve ownership and are created when their milestones need actual behavior:

| Location | Planned files |
| --- | --- |
| Package root | `settings.py` for validated runtime configuration; `bootstrap.py` for concrete composition. |
| `contracts/` | `requests.py`, `targets.py`, `observations.py`, `actions.py`, `surfaces.py`, `conditions.py`, `capabilities.py`, `runs.py`, `sessions.py`, `interventions.py`, `providers.py`. |
| `application/` | `run_coordinator.py`. |
| `discovery/` | `model_client.py`, `discovery_engine.py`; under `providers/`: `openai_client.py`, `anthropic_client.py`, `gemma_client.py`. |
| `capabilities/` | `capability_builder.py`, `capability_validator.py`, `capability_store.py`. |
| `replay/` | `state_evaluator.py`, `replay_engine.py`. |
| `interaction/` | `policy_guard.py`, `session_controller.py`, `action_gateway.py`. |
| `surfaces/` | `surface_adapter.py`, `browser_surface_adapter.py`. |
| `intervention/` | `intervention_manager.py`. |
| `evidence/` | `redaction.py`, `evidence_recorder.py`. |
| `interfaces/` | `command_interface.py`, `http_interface.py`, `operator_interface.py`. |

No future teaching package is reserved yet. When P6 is authorized, teaching becomes a second authoring path into the existing Validator, Store, Policy Guard, Action Gateway, Session Controller, Replay Engine, and evidence controls.

## Dependency rules enforced in P1.0

The static architecture test parses production imports and currently checks:

1. Contracts do not import other production subsystems or known provider/browser SDKs.
2. Replay does not import discovery, interfaces, known provider SDKs, or Playwright.
3. A future `state_evaluator.py` does not import discovery, surfaces, known provider SDKs, or Playwright.
4. Production Playwright imports occur only in `surfaces/browser_surface_adapter.py`.
5. OpenAI and Anthropic SDK imports occur only in their corresponding provider adapters; discovery core cannot import those SDKs.
6. Evidence does not import application, discovery, or replay engines.
7. Production runner modules do not import `demo_app` or `tests`.
8. Package initializers contain only docstrings, imports/re-exports, and constant assignments.

Additional accepted rules remain code-review and future-test obligations: gateway/session components depend on the Surface Adapter interface; concrete wiring belongs in `bootstrap.py`; higher-level engines never receive raw browser handles; provider adapters return normalized contracts; interfaces do not duplicate workflows; and imports must remain acyclic.

Static import checks have limits. They cannot prove that replay avoids dynamic model calls, that evidence is private, that a browser action was authorized at runtime, that imports themselves are harmless, or that reflection/dynamic imports do not bypass a rule. Focused unit, integration, process-isolation, and end-to-end tests are still required.

## Generic Discovery milestone additions

These files extend existing owners; they do not introduce services or a second execution engine.

| Location | Responsibility |
| --- | --- |
| `contracts/browser_discovery.py` | Strict observations, ephemeral-ref decisions, application identity and package data. |
| `discovery/browser_discovery.py` | Bounded unprofiled strategy reached through DiscoveryEngine. |
| `surfaces/browser_observation.py` | Pure URL-scope, normalization and fingerprint helpers; browser handles remain in BrowserSurfaceAdapter. |
| `capabilities/binding_compiler.py` | Deterministic observed bindings and semantic capability compilation using the existing Builder. |
| `bootstrap.py` | Fresh package Replay composition, application identity checks and no ModelClient. |
| `demo_app/discovery_workspace.py` | Process-local product composition, explicit application allowlist and artifact routes. |
| `demo_app/legacy_bank_b.py` | Second synthetic banking fixture, never imported by production engines. |
| `demo_app/evaluation.py`, `demo_app/eval_model.py`, `evals/` | Explicit scripted/live workflow evaluations and local reports. |
| `scripts/verify_discovery_workspace.py`, `scripts/verify_workspace_handoff.py` | Real product UI walkthrough checks and selected captures. |
