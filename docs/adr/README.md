# Architecture Decision Register

A decision record explains a choice, the alternative we rejected and when we
would revisit it. The accepted decisions remain in the expandable record.

## Decisions at a glance

| Decision | Reason | Main cost |
| --- | --- | --- |
| One backend process | Keep session/control transitions easy to reason about. | No crash recovery for active browsers. |
| Separate Discovery and Replay | Use model reasoning only when finding the procedure. | Replay cannot improvise around new UI states. |
| Shared Action Gateway | Central policy and ownership checks for automation. | Careful ordering and concurrency tests are needed. |
| Typed JSON interpreter | Review data rather than execute generated code. | The supported action language is bounded. |
| Playwright adapter | Real browser behavior behind one surface contract. | Desktop remains a separate implementation. |
| Explicit ownership state | Prevent stale automation from racing a human. | Handback needs fresh validation. |
| Provider-neutral client | Keep provider formats out of the execution core. | Each provider needs its own compatibility tests. |
| Local JSON and safe event logs | Easy to run and inspect. | No distributed storage or universal PII detection. |
| Core before teaching | Finish the required thread before optional breadth. | Voice and Teach remain absent. |
| One responsibility-based package | Keep dependencies visible without extra services. | Boundaries need tests and review. |

## How to read the original record

**ACCEPTED BASELINE** means approved direction. **PROPOSED IMPLEMENTATION DETAIL**
means unresolved at the time of writing. **VERIFIED BEHAVIOR** requires a completed
check in [progress](../progress.md).

The later [native handoff decision](../subsystems/direct-browser-handoff.md)
amends the original rule for physical human input only. It happens directly in
the retained browser; every automated action still uses the gateway.
Historical phase gates and pending details below must be read with later
authorization and evidence, not as current implementation status.

<details>
<summary>Full accepted decisions, alternatives, assumptions and revisit conditions</summary>

This register is the source of truth for architecture status. It records decisions already accepted by the owner without implying that they are implemented or verified.

## Status vocabulary

- **ACCEPTED BASELINE**: architecture or product direction already agreed with the owner.
- **PROPOSED IMPLEMENTATION DETAIL**: a necessary detail that remains open. A proposal is not approval.
- **VERIFIED BEHAVIOR**: a claim backed by a named, completed test or experiment and linked evidence.

Architecture acceptance is not **VERIFIED BEHAVIOR**. Validation items in ADR-001 through ADR-009 remain test specifications unless `docs/progress.md` records a completed result. Examples are illustrative.

## Accepted decisions

### ADR-001: Modular monolith and shared backend core

- **Status:** ACCEPTED BASELINE.
- **Decision:** Build a modular monolith with a Python backend and typed Pydantic contracts. A command interface and a thin web interface call the same backend core; the product frontend is React and TypeScript. The Run Coordinator coordinates run lifecycle but does not choose individual UI actions.
- **Constraints:** A live browser session, control ownership, policy checks, evidence, discovery, and replay must remain coordinated for a complete vertical slice. P0 must not add distributed infrastructure. Both command-driven evidence generation and a usable operator/product UI are required paths into the same behavior.
- **Responsibilities and boundaries:** Domain modules expose typed contracts rather than importing CLI, HTTP, or React concerns. CLI and web handlers adapt input and output only. The Run Coordinator may start, pause, resume, stop, and report runs; it delegates model decisions to Discovery Engine and prescribed execution to Replay Engine.
- **Fit for this assignment:** Local coordination keeps the same-session handoff and end-to-end demo understandable while module boundaries permit focused tests and later extraction.
- **Alternatives:** Separate services for discovery, replay, policy, and sessions; a browser-only TypeScript application.
- **Why not selected now:** Services add network failure modes, deployment work, and distributed ownership before scale is exercised. Browser-only TypeScript weakens the accepted Python/Pydantic contract core and does not simplify the live-session ownership problem enough to justify changing it.
- **Disadvantages and failure modes:** One process is a shared failure boundary. Workloads cannot scale independently. Poor import discipline could turn modules into an implicit monolith, and blocking provider or file operations could stall asynchronous browser work.
- **Unverified assumptions:** A single process can support the assignment's discovery, replay, and one operator handoff without unacceptable event-loop contention. Typed module boundaries can prevent UI concerns from leaking into execution logic.
- **Validation:** Run one end-to-end concurrency test with an active browser plus operator handoff while measuring event-loop stalls; add import-boundary tests and contract tests showing CLI and web adapters return equivalent core results for the same illustrative request.
- **Revisit when:** Deployment needs independent scaling or isolation, one process cannot meet measured concurrency/reliability needs, or a module boundary has a clear network-worthy contract and operational owner.

### ADR-002: Separate discovery from deterministic replay

- **Status:** ACCEPTED BASELINE.
- **Decision:** Discovery Engine uses a provider-neutral Model Client to explore an observe-decide-act loop. Deterministic Replay Engine interprets a saved capability and has no Model Client dependency. A non-LLM State Evaluator is shared by both paths.
- **Constraints:** The assignment requires one real LLM-driven discovery run and a production path with no model making replay decisions. Both paths must recognize checkpoints and runtime outcomes consistently.
- **Responsibilities and boundaries:** Discovery proposes actions and records successful observations. Capability Builder converts the successful trace into a candidate definition. Replay executes only represented actions. State Evaluator evaluates explicit conditions and must not invoke a model. Dependency tests must prevent Replay Engine from importing Model Client or provider adapters.
- **Fit for this assignment:** It makes the central claim directly testable: the model discovers, while a reviewable artifact prescribes subsequent execution.
- **Alternatives:** Keep the model in every run; generate executable automation code from the discovery transcript.
- **Why not selected now:** Per-run model decisions are costlier, less reproducible, and violate deterministic replay. Generated code broadens the security and validation surface and is harder to inspect as data.
- **Disadvantages and failure modes:** Capabilities can express only actions, conditions, and outcomes supported by the schema and interpreter. Discovery may succeed through behavior that cannot be represented safely, so capability publication must fail rather than preserve an unreplayable trace.
- **Unverified assumptions:** The initial action and condition language is sufficient for the selected target's successful and exceptional paths. State Evaluator can classify required outcomes without semantic model judgment.
- **Validation:** Execute discovery, validate the candidate, then replay with provider credentials absent and network calls to model hosts blocked. Add a negative builder test where an unsupported discovered action is rejected. Run checkpoint fixtures through discovery and replay evaluators and compare classifications.
- **Revisit when:** Required workflows repeatedly fail validation because the language cannot represent safe behavior, or measured runtime variation requires a narrowly bounded recovery mechanism approved as a contract change.

### ADR-003: Shared Action Gateway for policy and ownership enforcement

- **Status:** ACCEPTED BASELINE.
- **Decision:** Discovery, replay, and operator-originated actions pass through one Action Gateway. The gateway consults Policy Guard and Session Controller before dispatching to a Surface Adapter. It rejects actions that are outside the allowlist, disallowed by risk policy, or stale for the current control owner/state.
- **Constraints:** Safety behavior and live-session ownership must not diverge among execution modes. Domains/routes, action types, and risky or irreversible actions require explicit policy. Secrets and raw sensitive values must not be written to artifacts or logs.
- **Responsibilities and boundaries:** Callers request typed actions but cannot dispatch surface input directly. Policy Guard decides authorization; Session Controller decides ownership and freshness; Action Gateway orders checks, dispatches authorized actions, and emits sanitized evidence. It does not decide the next discovery step or interpret whole capabilities.
- **Fit for this assignment:** One narrow enforcement point makes parity among discovery, replay, and handoff demonstrable in a small implementation.
- **Alternatives:** Put checks independently in each engine; rely on browser context restrictions alone.
- **Why not selected now:** Duplicated checks drift. Browser restrictions cannot classify action risk, enforce human approval, or reject a stale automation action after control transfer.
- **Disadvantages and failure modes:** The gateway is a shared critical component and throughput point. A bypass, check-order bug, or confused-deputy input could affect every mode. Its responsibility can grow too broad if decision logic is added.
- **Unverified assumptions:** Every mutating surface operation can be routed through the gateway. A small typed policy vocabulary can cover the demonstration without hidden bypasses.
- **Validation:** Add architecture tests that forbid direct Surface Adapter action calls from engines. Table-test allowed, blocked, risky, expired, wrong-owner, and stale-generation actions for discovery, replay, and operator principals. Verify denied actions never reach a fake adapter and evidence contains no configured secret/PII fixtures.
- **Revisit when:** A surface requires operations that cannot pass through the gateway, authorization semantics differ materially by surface, or gateway load/failure measurements justify partitioning while preserving one policy contract.

### ADR-004: Typed, versioned JSON capability interpreter

- **Status:** ACCEPTED BASELINE.
- **Decision:** Capability Builder emits typed, versioned JSON definitions; Capability Validator validates them; Capability Store persists accepted artifacts. Replay Engine interprets the data instead of executing generated code. Definitions include a callable contract, ordered actions, target descriptions, typed inputs, typed outputs, expected business outcomes, recoverable conditions, hard failures, and success checkpoints.
- **Constraints:** Capabilities must be serializable, reviewable, parameterized, agent-invocable, and replayable without arbitrary code. The contract must distinguish business outcomes from execution failures.
- **Responsibilities and boundaries:** Pydantic models define serialization and validation. Builder may create only schema-supported constructs. Validator rejects unsafe, ambiguous, unsupported, or incompatible definitions before storage. Store handles persistence, not execution or approval logic. Replay supports declared schema versions explicitly.
- **Fit for this assignment:** JSON is easy to inspect in `/evidence/`, while typed validation makes the execution contract and limited language explicit.
- **Alternatives:** Store raw model transcripts; emit Playwright/Python source; adopt a general workflow engine or DSL.
- **Why not selected now:** Transcripts are not stable callable contracts. Generated source permits behavior beyond the policy language. A general workflow platform adds concepts and dependencies not exercised by the vertical slice.
- **Disadvantages and failure modes:** The action/condition language must be deliberately limited and evolved through versions. Migrations and compatibility need care. A valid document can still be semantically unsafe or target an ambiguous control, so schema validation alone is insufficient.
- **Unverified assumptions:** A compact discriminated action/condition set can represent the chosen flow and its required errors. Human reviewers can understand definitions without consulting raw discovery transcripts.
- **Validation:** Round-trip representative definitions through JSON and Pydantic; reject unknown schema versions, undeclared parameters, secret literals, unsupported actions, ambiguous targets, and missing terminal outcomes. Conduct a review exercise in which a reviewer identifies inputs, outputs, risky actions, and success condition from the artifact alone.
- **Revisit when:** Version migrations dominate maintenance, reviewers cannot assess behavior from the artifact, or workflows need composition that cannot be added without turning the interpreter into an unsafe general-purpose language.

### ADR-005: Asynchronous Playwright adapter with hybrid observation

- **Status:** ACCEPTED BASELINE.
- **Decision:** The initial Browser Surface Adapter uses asynchronous Playwright. Discovery may receive visual context plus browser structure/accessibility information, but every recorded browser target must be converted to and validated as a model-free target description before publication. Unsupported or ambiguous controls are rejected.
- **Constraints:** The discovery run must operate a real UI. The design must acknowledge hostile or non-semantic surfaces and later desktop adapters, while deterministic replay needs resolvable targets. Visual recognition alone does not produce a durable locator.
- **Responsibilities and boundaries:** Surface Adapter owns observation capture, target candidate resolution, actions, and surface-specific snapshots. Discovery chooses among validated candidates. Capability definitions describe target intent using adapter-neutral target records with surface-specific locator data; Replay asks the adapter to resolve them. State Evaluator consumes normalized observations.
- **Fit for this assignment:** Playwright supplies a practical real-browser implementation and rich evidence. Hybrid observation demonstrates awareness of visual/legacy constraints without allowing replay to depend on model vision.
- **Alternatives:** DOM-only locators; screenshot-coordinate control only; OS-level desktop automation for the initial target.
- **Why not selected now:** DOM-only control overstates semantic-markup availability. Raw coordinates are brittle and hard to parameterize. Desktop-first increases environment and demo complexity before the artifact and handoff contracts are proven.
- **Disadvantages and failure modes:** Async code introduces cancellation and cleanup complexity. Visual confidence does not guarantee target uniqueness. Browser locators do not prove desktop portability. Frames, canvases, duplicate labels, and variant branding can defeat an initial resolver.
- **Unverified assumptions:** The selected proxy target exposes enough browser/accessibility signal to validate replayable controls. Normalized observations can support the same State Evaluator contract for future adapters.
- **Validation:** Record and replay against the chosen target after benign viewport and timing changes; include fixtures with duplicate labels, iframes, missing semantic attributes, and an intentionally unsupported canvas control. Require unique resolution or explicit rejection. Implement a fake second adapter contract test before claiming surface neutrality.
- **Revisit when:** The target cannot yield stable validated locators, screenshot-derived targeting can be made deterministic with measured reliability, or desktop requirements reveal that the normalized target/observation contract contains browser-only assumptions.

### ADR-006: Explicit control state machine and same-session handoff

- **Status:** ACCEPTED BASELINE.
- **Decision:** Session Controller owns explicit control-state transitions. Intervention Manager raises requests with sanitized context. Operator Interface takes control of the same live session, records human actions through the shared gateway, and explicitly hands control back. Actions carry freshness information and stale actions are rejected.
- **Constraints:** Automation must pause, transfer ownership, and resume without opening a fresh session. Risk approvals and stuck states require inspectable ownership. A persisted step number alone cannot restore a browser or prove who controls it.
- **Responsibilities and boundaries:** Session Controller is authoritative for state and owner; Intervention Manager manages request lifecycle and context; Run Coordinator responds to state transitions; Operator Interface renders/control-signals but does not bypass policy. Surface Adapter retains the live session until completion or cleanup.
- **Fit for this assignment:** A small explicit state machine makes the required handoff real and testable without building a production co-browsing service.
- **Alternatives:** Boolean pause flag; separate operator browser session; unrestricted simultaneous input.
- **Why not selected now:** A flag does not encode owner or legal transitions. A fresh session loses state. Simultaneous input creates races and defeats safety review.
- **Disadvantages and failure modes:** Correct synchronization, cancellation, and cleanup are difficult. Delayed actions can arrive after ownership changes. Process failure loses the live session; persisting state metadata does not provide crash recovery.
- **Unverified assumptions:** A single-process controller can serialize transitions and reject all delayed actions. Playwright can expose a usable same-session operator view/control path for the chosen environment.
- **Validation:** Model-test every legal and illegal transition; race a delayed automation action against operator takeover and require rejection; test disconnect, timeout, duplicate resume, and cleanup. Perform a manual handoff on one live session and preserve correlated evidence before claiming verified behavior.
- **Revisit when:** Multi-process control is required, crashes must preserve resumable sessions, or the operator mechanism cannot safely share the chosen live surface.

### ADR-007: Provider-neutral Model Client with three adapters

- **Status:** ACCEPTED BASELINE.
- **Decision:** Discovery depends on a provider-neutral Model Client. Provide adapters for OpenAI, Anthropic, and hosted Gemma. Provider SDK types and message formats do not cross the adapter boundary.
- **Constraints:** Provider choice must remain deployable and testable without coupling discovery to one vendor. The assignment requires a genuine model-driven run, while provider feature support differs.
- **Responsibilities and boundaries:** Discovery sends normalized observations, allowed actions, and tool/result contracts. Adapters translate requests, structured outputs/tool calls, errors, timeouts, and usage metadata. Provider selection/configuration occurs at composition time. Replay has no dependency on this boundary.
- **Fit for this assignment:** The seam demonstrates portability while keeping model variability out of deterministic execution.
- **Alternatives:** Implement one provider directly in Discovery Engine; use a broad third-party model abstraction framework.
- **Why not selected now:** Direct integration creates vendor coupling. An additional abstraction framework can obscure exact computer-use and structured-output differences and adds a dependency not otherwise needed.
- **Disadvantages and failure modes:** A lowest-common-denominator interface can hide useful features. Tool calling, image input, token limits, safety behavior, and error semantics differ. An adapter name does not prove a deployed Gemma endpoint supports required modalities.
- **Unverified assumptions:** One normalized request/response contract can support the selected discovery loop across all three adapters. Each configured deployment supports the required image and/or structured action protocol.
- **Validation:** Run adapter contract tests with recorded/synthetic provider responses, then a deployment capability probe for each configured model. Record supported modalities, structured-output behavior, timeout/error mapping, and one real discovery run for the selected provider; do not infer parity from mocks.
- **Revisit when:** Provider capabilities require materially different discovery strategies, the common interface loses essential information, or maintaining direct adapters costs more than an evaluated library saves.

### ADR-008: Local JSON storage and sanitized JSONL evidence

- **Status:** ACCEPTED BASELINE.
- **Decision:** The initial Capability Store uses versioned JSON files. Evidence Recorder writes sanitized JSONL run events plus approved richer failure evidence such as screenshots or snapshots. Artifacts and evidence never intentionally persist credentials, tokens, or raw sensitive data.
- **Constraints:** Reviewers need reproducible local artifacts and logs. P0 must avoid database/queue infrastructure. Regulated-data handling requires minimization and redaction before persistence.
- **Responsibilities and boundaries:** Store owns atomic local capability reads/writes and version checks. Evidence Recorder owns event envelopes, correlation, redaction, and approved attachments. Callers submit typed fields; they do not write ad hoc logs. Policy/configuration identifies sensitive fields and retention limits.
- **Fit for this assignment:** Files are easy to inspect, commit as sanitized examples, and use in deterministic demos.
- **Alternatives:** SQLite; relational/object storage with a telemetry backend; raw Playwright traces and transcripts.
- **Why not selected now:** Production storage adds migration and operations work outside the vertical slice. Raw traces/transcripts can capture secrets and PII and are too broad as the default evidence format.
- **Disadvantages and failure modes:** Concurrent publication, indexing, access control, retention, and large attachments are limited. Redaction can miss secrets in screenshots or unstructured text. File corruption and partial writes require deliberate handling.
- **Unverified assumptions:** Structured-field redaction plus bounded approved attachments is sufficient for the synthetic demo data. Atomic replace and single-writer constraints are adequate for local execution.
- **Validation:** Use canary secrets and synthetic PII across actions, errors, URLs, model responses, screenshots, and snapshots, then scan persisted bytes. Inject interrupted writes and concurrent publish attempts. Verify malformed files fail closed and retention cleanup removes the intended run only.
- **Revisit when:** Multiple writers or hosts are required, evidence volume/query needs exceed files, access/retention controls need central enforcement, or redaction tests show unstructured evidence cannot be made safe enough.

### ADR-009: Required execution core before teaching features

- **Status:** ACCEPTED BASELINE.
- **Decision:** Build the assignment's required goal-to-discovery-to-capability-to-replay path, including safety, evidence, and same-session intervention, before optional teaching features. A later Teams-like voice-and-screen teaching experience is a second capability-authoring path that reuses Capability Validator, Capability Store, Policy Guard, Action Gateway, Session Controller, and Replay Engine.
- **Constraints:** The assignment evaluates a complete thin vertical slice and explicitly values depth over breadth. Teaching does not replace the required genuine LLM discovery run.
- **Responsibilities and boundaries:** Future teaching translates human-guided actions into candidate capability definitions; it does not create a separate artifact format, safety path, or replay implementation. React UI may later host teaching interaction after the execution core is proven.
- **Fit for this assignment:** It protects the required execution path and tests the reusable authoring boundary before investing in richer interaction.
- **Alternatives:** Build teaching first; combine human teaching and LLM discovery into one authoring engine immediately; omit teaching permanently.
- **Why not selected now:** Teaching-first risks a polished UI without the required discovery and replay core. Early unification obscures distinct evidence/provenance. Permanent omission would ignore the accepted product direction.
- **Disadvantages and failure modes:** The richer user experience arrives later. If core contracts accidentally encode model-specific provenance or observations, teaching integration may expose redesign needs.
- **Unverified assumptions:** Validator, policy, store, and replay contracts are author-neutral. A human action stream can be normalized into the same candidate schema without weakening provenance or review.
- **Validation:** Before teaching implementation, feed an illustrative manually authored candidate through Validator and Replay contract tests with explicit human provenance. Reject any path that needs to bypass policy or add executable code to the artifact.
- **Revisit when:** The required assignment path is verified and owner authorizes the teaching phase, or evidence shows a shared candidate contract cannot represent human-authored flows without a reviewed schema change.

### ADR-010: One source package with responsibility-aligned modules

- **Status:** ACCEPTED BASELINE.
- **Decision:** Place production Python code in one `src/capability_runner/` package, with subsystem directories matching accepted component responsibilities. Keep the React client in `web/`, the operated synthetic target in `demo_app/`, local runtime data in ignored `var/`, curated real evidence in `evidence/`, and test-only artifacts in `tests/fixtures/`. Keep package initializers side-effect free and enforce practical import boundaries with static architecture tests.
- **Constraints:** P1.0 must make ownership visible without creating empty implementations for future work. The modular monolith needs one composition root, no duplicate backend, and no accidental imports of demo/test data. Public-repository hygiene must separate local secrets/runtime data from reviewed evidence and references.
- **Responsibilities and boundaries:** `contracts/` owns shared data agreements; each other package owns its named behavior. Concrete dependency wiring belongs in planned `bootstrap.py`, not package import side effects. Planned `settings.py` owns validated configuration when needed. `web/` calls the thin backend; `demo_app/` remains an external target. `docs/repository-map.md` is the detailed ownership map.
- **Fit for this assignment:** A conventional `src/` package prevents accidental root imports, makes the accepted modular boundaries reviewable, and keeps local setup small enough for the required vertical slice.
- **Alternatives:** A flat package with all modules together; separate installable packages/services per component; creating every planned file as a placeholder.
- **Why not selected now:** A flat package obscures ownership as the slice grows. Separate packages/services add packaging and deployment boundaries not exercised by this assignment. Placeholder files imply progress and create speculative interfaces before their consumers exist.
- **Disadvantages and failure modes:** Directories alone do not enforce architecture. Static import tests can miss dynamic imports and cannot prove privacy, authorization, or model-free runtime behavior. Too many package boundaries could encourage ceremony if contracts are added ahead of need.
- **Unverified assumptions:** The chosen packages remain cohesive as the vertical slice develops. AST import checks provide useful early feedback without becoming brittle. A single composition root can wire the required local workflow cleanly.
- **Validation:** Import all package markers in a clean subprocess and assert no runtime files/provider/browser modules appear; parse production imports for the documented forbidden edges; run lint and type checks; revisit rules as concrete interfaces are introduced. Record exact results in `docs/progress.md`.
- **Revisit when:** A package repeatedly owns unrelated behavior, a necessary dependency cannot be expressed without a cycle, static rules generate persistent false positives, or measured deployment needs justify an independently owned boundary.

## Proposed implementation details

These questions are unresolved. Recommendations are starting points for owner review where they affect public contracts, security, data handling, significant dependencies, or scope.

| ID | Status | Constraint and alternatives | Recommendation and downside | Decision test / approval trigger |
| --- | --- | --- | --- | --- |
| PDI-001 | PROPOSED IMPLEMENTATION DETAIL | Control transfer needs serialization and stale-action rejection. Options include an async lock plus monotonic control generation, a command queue, or durable leases. | Start locally with an async lock, explicit transition table, owner principal, and monotonic generation attached to every action. It is not crash recovery and cannot coordinate processes. | Race and transition model tests. Owner approval before this shape becomes a public session/control contract. |
| PDI-002 | PROPOSED IMPLEMENTATION DETAIL | The exact action, condition, target, input/output, outcome, and migration schema is undecided. Options include discriminated Pydantic unions or a general expression/workflow language. | Use small discriminated unions and explicit schema-version handlers; reject unknown constructs. This requires deliberate additions for new behavior. | Prove the selected happy path and required exceptional paths can be represented. Owner approval is required because this is the central public artifact contract. |
| PDI-003 | PROPOSED IMPLEMENTATION DETAIL | Browser targets need ordered strategies and uniqueness rules. Options include accessibility-first candidates, CSS/XPath, visual anchors, or coordinates. | Store target intent plus validated adapter-specific candidates; require unique resolution and disallow raw coordinates in initial published browser capabilities unless explicitly bounded. Some hostile controls will be rejected. | Fixture matrix for duplicates, frames, variant labels, and unsupported controls. Owner approval if coordinate targets or model-assisted replay are introduced. |
| PDI-004 | PROPOSED IMPLEMENTATION DETAIL | Recoverable retries need bounded predicates. Options include per-step policy, global defaults, or unrestricted retries. | Define explicit retryable observation/error codes with per-step bounded attempts and backoff caps; never retry risky actions after uncertain dispatch. More workflows will escalate instead of self-heal. | Fault-injection tests for slowness, navigation failure, duplicate submission risk, and known interstitials. Approval required for retry semantics on irreversible actions. |
| PDI-005 | PROPOSED IMPLEMENTATION DETAIL | Redaction and retention must cover structured and visual evidence. Options include allowlisted evidence fields, denylist redaction, OCR/image masking, or disabling screenshots. | Persist allowlisted structured fields, use synthetic demo data, bound attachment count/size, and disable unsafe attachments when masking confidence is insufficient. Debug evidence may be reduced. | Canary-secret byte scan and screenshot/snapshot review. Owner approval before any policy that permits potentially sensitive screenshots or defines retention. |
| PDI-006 | PROPOSED IMPLEMENTATION DETAIL | OpenAI, Anthropic, and hosted Gemma expose different modalities and structured-action features. Options include one minimal common contract or capability-negotiated extensions. | Begin with a minimal normalized contract plus explicit adapter capability declarations; fail configuration when the chosen discovery mode is unsupported. The interface may not expose provider-specific optimizations. | Deployment probes and one provider contract suite per adapter. Provider/model versions and hosted Gemma endpoint remain deployment choices. |
| PDI-007 | PROPOSED IMPLEMENTATION DETAIL | Live operator control can use a Playwright-backed local page, browser/CDP attachment, or a proxied remote viewer. | For the local milestone, expose a minimal authenticated operator route/view bound to the existing run and gateway; exact transport remains open. A local approach does not establish production remote access security. | Same-session takeover/resume experiment plus unauthorized/stale client tests. Owner approval is required for the operator access/authentication contract and any remote exposure. |
| PDI-008 | PROPOSED IMPLEMENTATION DETAIL | File persistence needs publication and cleanup semantics. Options include single-writer atomic replace, file locks, or SQLite. | Use single-writer atomic temporary-write/replace with explicit retention cleanup limits for the initial local implementation. This does not support multi-host writers or rich querying. | Interrupted-write and concurrent-publish experiments. Revisit before concurrent writers or production retention requirements. |

## Contradictions and unsupported assumptions

- No contradiction in the accepted baseline is known at P0.
- Surface neutrality, cross-provider parity, target robustness, safe visual evidence, and same-session synchronization are architectural intentions, not verified behaviors.
- Supporting three provider adapters does not mean every model deployment supports image input, tool use, or schema-constrained output; PDI-006 requires deployment probes.
- Persisting control metadata does not make a Playwright session crash-resumable.
- A typed JSON artifact is syntactically constrained, not automatically safe or semantically replayable; Policy Guard, target validation, and execution tests remain required.
- File-based storage is accepted for the initial local implementation only; no concurrency or scale claim follows from that acceptance.

## Change rule

Accepted decisions are implemented within their authorized milestone. Alternatives remain context, not invitations to redesign. A failing experiment or concrete contradiction must be recorded here with its evidence, the smallest necessary change, and consequences; work affected by that change pauses for owner review. New public contracts, security/data-handling policy, significant dependencies, or scope changes require owner approval.

</details>
