# Frontend Implementation

The React frontend is implemented. This is its initial implementation record. Current native handoff and test results are recorded in progress.

See [the screenshot guide](../submission/test-product.md) and
[progress](../progress.md) for the reviewer path and current evidence.

<details>
<summary>Detailed visual record</summary>

## Scope

P5.4b implements the optional React product/demo surface from the complete four-image reference set
under `docs/references/ui/current/`. P1-P5.4a runtime semantics remain frozen. The UI is a client of
existing components, not a second workflow engine. Voice and screen-sharing integration remain P6.

## Stack

- React, TypeScript, and Vite under `web/`.
- React Router for stable product routes.
- Lucide React for the reference icon vocabulary.
- Manrope packaged locally through `@fontsource/manrope`.
- Explicit CSS tokens/layout for visual fidelity; no admin-template or component framework.
- Vitest and Testing Library for behavior-oriented frontend tests.
- Flask demo-owned composition for local product APIs and built static assets.

## Ownership and dependency boundary

The browser client owns presentation state, route selection, pending/error display, form masking, and
safe polling. It does not own policy, model/provider calls, workflow interpretation, browser
operations, evidence redaction, or intervention ownership.

`demo_app/product_http.py` is the local review composition because it may legally combine the
synthetic CoreBank target and the production Capability Runner package. Production code under
`src/capability_runner/` must not import `demo_app`. HTTP handlers remain thin:

- artifact reads parse only JSON/JSONL beneath explicitly configured `evidence/` and
  `var/demo-runs/` roots;
- Discovery delegates to existing `run_through_line` composition and accepts only the supported
  reviewer goal/profile rather than pretending arbitrary goals work;
- Replay delegates to the existing model-free Replay composition through an additive demo wrapper;
- live intervention setup reuses the P4.2/P4.3 manager, console, gateways, session controller,
  browser adapter, and continuation coordinator;
- operator action/view/return/stop routes call `OperatorConsoleService` and never dispatch directly.

## HTTP contract

All errors use `{ "error": { "code": string, "summary": string } }`. Sensitive runtime values are
accepted only in request bodies, never echoed, persisted in summaries, or included in event DTOs.

| Method | Route | Owner/delegate | Notes |
| --- | --- | --- | --- |
| GET | `/api/overview` | product read adapter | Counts only parsed real local artifacts; unavailable health is explicit. |
| GET | `/api/capabilities` | product read adapter + `CapabilityDefinition` validation | Dedupe actual capability id/version files. |
| GET | `/api/capabilities/:id` | same | Optional `version`; latest actual semantic version by default. |
| GET | `/api/runs` | product read adapter | Sanitized summaries only, newest first. |
| GET | `/api/runs/:runId` | product read adapter | Summary plus safe derived state. |
| GET | `/api/runs/:runId/events` | product read adapter | Parsed sanitized `EvidenceEvent` envelopes. |
| POST | `/api/discovery` | existing `run_through_line` | Fixed trusted CoreBank profile and supported reviewer goal; synchronous bounded request. |
| POST | `/api/replay` | existing Replay composition | Actual capability id/version plus masked `member_id`; model-free. |
| GET | `/api/interventions` | persisted H-02 evidence + active runtime | No invented history. |
| POST | `/api/interventions` | existing P4.2/P4.3 composition | Starts one managed local live intervention when none is active. |
| GET | `/api/interventions/:id` | active `OperatorConsoleService` or persisted safe record | Active status has authoritative owner/generation. |
| GET | `/api/interventions/:id/view` | existing `SurfaceView` | Active session only; `no-store`; no screenshot persistence. |
| GET | `/api/interventions/:id/controls` | existing operator console | Visible trusted semantic controls only. |
| POST | `/api/interventions/:id/actions` | existing operator console | Typed fill/click request; values never echoed. |
| POST | `/api/interventions/:id/return-control` | console then continuation coordinator | Fresh validation and existing safe resume semantics. |
| POST | `/api/interventions/:id/stop` | existing operator console | Terminal cleanup. |

## Client routes

| Route | Data and behavior |
| --- | --- |
| `/` | Actual capability/run/intervention counts and recent runs; unavailable health/environment values are explicit. |
| `/discover` | Supported natural-language goal, trusted CoreBank profile, pending state, and safe result/timeline. |
| `/capabilities` | Actual list and selected detail rail. |
| `/capabilities/:capabilityId` | Same split layout deep-linked to an actual capability. |
| `/runs` | Actual local/curated summaries or empty state. |
| `/runs/:runId` | Safe E-01 timeline and structured result/business outcome/failure. |
| `/interventions` | Actual persisted and active interventions or empty state. |
| `/interventions/:interventionId` | H-02 detail; active SurfaceView/semantic controls when the managed session is live. |
| `/teach` | Reference-consistent shell with P6-only voice/share controls disabled and explicitly unconnected. |
| `/sessions` | Truthful current-process limitation and active intervention session when present. |
| `/evidence` | Safe event navigation into actual runs. |
| `/settings` | Nonsecret local presentation/configuration information only. |

## State and failure behavior

- Fetch state uses component-local React state; no global state framework.
- Mutations disable duplicate submission and render safe backend error summaries.
- Discovery and Replay never optimistically claim success.
- Missing runtime history produces an empty state, not fixture rows.
- Persisted intervention records are labeled completed/historical and expose no live controls.
- Active intervention views are requested with cache busting and are never stored by the client.
- Teach media buttons remain disabled with `Not connected - P6` status.

## Security and privacy

- Sensitive fields use `type="password"` with an explicit reveal control.
- The client types only public DTO fields and never requests provider configuration.
- Timeline rendering maps allowlisted reason codes/metadata to human labels; raw JSON is secondary and
  not the primary experience.
- No raw goal, runtime input map, provider response, selector, HTML, private endpoint, or credential
  is rendered.
- The server resolves requested files by validated identifiers and fixed roots; paths are never
  accepted from the client.

## Validation

1. Frontend route/navigation, Discovery submit, capability/run/intervention loading, timeline,
   outcome/failure, operator actions, return control, sensitive masking, and safe error tests.
2. TypeScript typecheck and production Vite build.
3. Python route/service tests for safe parsing, traversal rejection, real workflow delegation, and
   operator route delegation.
4. One screenshot and up to three correction passes for each of the four reference-defined states at
   `1448 x 1086`, stored under `docs/references/ui/implemented/`.
5. Full Python gates only because P5.4b adds backend source/tests; existing CLI help and commands are
   rechecked and E-01/H-02 evidence remains unchanged.

</details>
