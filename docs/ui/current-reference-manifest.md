# Current UI Reference Manifest

This records the visual inputs used during frontend design. Image names and counts are historical; they do not establish current product behavior.

See [the screenshot guide](../submission/test-product.md) and
[progress](../progress.md) for the reviewer path and current evidence.

<details>
<summary>Detailed visual record</summary>

## Audit scope

The complete visual source is `docs/references/ui/current/`. It contains four PNG files, all
`1448 x 1086`. Every file was enumerated and visually inspected on 2026-09-12. No file is ignored
or unresolved. The primary implementation and screenshot-comparison viewport is therefore
`1448 x 1086`.

Reference images define visual treatment and composition. Backend state remains authoritative:
illustrative counts, people, capabilities, run durations, URLs, health claims, and outcomes shown
in the images must not be reproduced as runtime facts unless the backend supplies them.

## Reference inventory

| Reference | Apparent page | Apparent state | Route | Implementation |
| --- | --- | --- | --- | --- |
| `docs/references/ui/current/home.png` | Home | Populated overview | `/` | implemented; fidelity PASS |
| `docs/references/ui/current/capability-library.png` | Capabilities | Library with first capability selected and detail rail open | `/capabilities` | implemented; fidelity PASS |
| `docs/references/ui/current/run-detail.png` | Run detail | Running, first workflow stage active | `/runs/:runId` | implemented; fidelity PARTIAL |
| `docs/references/ui/current/human-intervention.png` | Intervention detail | Paused, intervention requested, operator has not yet taken control | `/interventions/:interventionId` | implemented; fidelity PASS |

## Per-reference analysis

### `home.png`

- **Page/state:** populated Home overview.
- **Navigation selected:** Home. Navigation order is Home, Discover, Runs, Capabilities, Sessions,
  Evidence, Settings.
- **Header:** page label `Home`; centered search field; notification icon; circular avatar and
  two-line user identity with a disclosure chevron.
- **Main structure:** full-width greeting banner; three equal workflow action cards; four compact
  metric cards; a five-row Recent Runs table. A narrow right rail contains System Health,
  Environment, and Need help panels.
- **Visible actions:** Browse Capabilities, Create a Capability, Start a Run, View all, row overflow,
  View system status, Open Help Center.
- **Cards/tables:** square-cornered-to-soft cards with thin cool-gray borders, subtle shadow, and
  approximately 8px radius. Recent Runs uses compact 49px rows and no outer section nesting.
- **Badges:** green Completed, blue Running, amber Needs Review, plus compact environment/status
  chips.
- **Typography:** large greeting around 43px/1.1, page title around 25px, card headings around
  18px, body 14-16px, compact labels 12-13px. Weight is strongest for page/card titles.
- **Color:** dark navy shell; white cards; very pale blue canvas; vivid royal-blue primary actions;
  mint success, lavender teaching, amber review.
- **Approximate geometry:** 226px sidebar, 70px header, 25px page gutter, 172px hero, 250px right
  rail, 15-18px card gaps. Main content begins near x=251.
- **Truth constraint:** all shown counts, health, environment, identity, and recent-run rows are
  illustrative. Render computed local data or explicit unavailable/empty states.

### `capability-library.png`

- **Page/state:** capability library with one selected capability and its details visible.
- **Navigation selected:** Capabilities.
- **Header:** page label `Capabilities`; otherwise shared header.
- **Main structure:** two-column body. Left library pane has title/subtitle, New Capability,
  category tabs, search, filter action, a dense table-like capability list, and pagination. Right
  detail rail has identity/status, primary run action, evidence/version actions, input/output
  schemas, description, owner, and last replay result.
- **Visible actions:** New Capability, filter tabs, search, Filters, row overflow, Run Capability,
  View Evidence, Open Version History, schema collapse toggles, View run, pagination.
- **Tables/cards/forms:** selected row has blue outline and pale blue fill. Rows are about 73px tall.
  Detail rail is one 368px-wide unframed/card surface with horizontal dividers.
- **Badges:** Ready (green), In Review (amber), Draft (gray), plus input/output/type chips.
- **Typography:** 34px library heading, 17px subtitle, 14-16px rows, 12-13px metadata and chips.
- **Color:** same shell and surfaces; blue focus/selection, mint/amber/gray statuses.
- **Approximate geometry:** 226px sidebar, 70px header, 20px page gutter, 800px library region,
  368px detail rail, 14px inter-column gap.
- **Truth constraint:** only actual `CapabilityDefinition` files may be listed. Unsupported owner,
  approval, history, or replay metadata must be omitted or shown as unavailable.

### `run-detail.png`

- **Page/state:** active/running capability execution, currently at Search Member.
- **Navigation selected:** Home in the reference, despite the Runs breadcrumb. Preserve this visual
  state for the reference route screenshot rather than silently claiming the image selects Runs.
- **Header:** page label `Home`; shared search/profile header.
- **Main structure:** breadcrumb; run title, Running badge, elapsed time, overflow and View
  Capability actions; five-stage horizontal progress strip; large Application Preview at left;
  Agent Activity timeline and Run Details panels at right; sticky-style action bar at bottom.
- **Visible actions:** overflow, View Capability, open preview, Pause, Stop Run.
- **Timeline:** completed green node, active blue ring, pending gray nodes connected vertically;
  safe labels and timestamps only.
- **Badges:** Running (mint/green), Connected to CoreBank (mint).
- **Typography:** 38px run title, 16px supporting text, 17px panel titles, 13-14px timeline/details.
- **Color:** same shell; blue progress/active state; green connection/completion; red stop action.
- **Approximate geometry:** 226px sidebar, 70px header, 25px gutter; 1170px content width; progress
  strip 134px high; main grid approximately 830px/330px; 18px gap.
- **Truth constraint:** the application preview must use an approved current SurfaceView when a
  managed session exists. For persisted completed runs, show structured evidence and an honest
  unavailable-live-view state rather than a fabricated browser.

### `human-intervention.png`

- **Page/state:** paused run requiring a human intervention before control transfer.
- **Navigation selected:** Home in the reference, despite the Runs breadcrumb.
- **Header:** page label `Home`; shared search/profile header.
- **Main structure:** breadcrumb and paused run title; prominent lavender intervention banner with
  Take Control/View Instructions; live browser region left; Intervention Details rail right; bottom
  return/cancel action bar.
- **Visible actions:** More actions, Take Control, View Instructions, Open in New Window, Return
  Control to Agent, Cancel Handoff.
- **Forms/live view:** reference browser shows a login form, but implementation must render only the
  existing bounded ephemeral SurfaceView and existing trusted semantic controls. No arbitrary
  selector or coordinate interaction.
- **Details:** reason, current step, requested time, handoff state, session owner, and a green secure
  session notice. Claims such as recording/auditing must be softened to what evidence supports.
- **Badges:** Paused coral pill; green secure/connected indicators.
- **Typography:** 38px run title, 22px intervention heading, 17px panel titles, 13-15px detail copy.
- **Color:** pale lavender intervention banner; royal-blue controls; coral pause/reason; mint safety
  notice; shared navy shell and pale canvas.
- **Approximate geometry:** 226px sidebar, 70px header, 25px gutter; banner 128px high; main grid
  approximately 760px/395px; bottom bar 84px.
- **Truth constraint:** reason, blocked step, control generation/owner, semantic controls, view,
  return, and stop come from the existing P4.2/P4.3 path. No second intervention engine.

## Screen coverage checklist

| Screen | Reference images | Required reference states | Route | Backend source | Status |
| --- | --- | --- | --- | --- | --- |
| Home | `home.png` | populated geometry; truthful empty/unavailable substitutions allowed | `/` | capability files, run summaries, intervention summaries | implemented and visually verified |
| Discover | none | no reference-defined state; initial/submitting/result states required by product integration | `/discover` | existing Discovery reviewer/application composition through thin HTTP adapter | implemented and client-tested |
| Capabilities | `capability-library.png` | library plus selected detail rail | `/capabilities` | actual `CapabilityDefinition` files from configured local stores/curated runtime data | implemented and visually verified |
| Capability detail | `capability-library.png` | selected detail rail | `/capabilities/:capabilityId` | actual `CapabilityDefinition` | implemented and client-tested |
| Runs | `home.png` (recent table only) | truthful available local runs/empty state | `/runs` | sanitized local runtime summaries | implemented and client-tested |
| Run detail | `run-detail.png` | structured running/completed/business-outcome/failure presentation | `/runs/:runId` | sanitized summary and E-01 evidence JSONL | implemented; fidelity PARTIAL for historical state |
| Interventions | none | truthful active/current-session list or empty state | `/interventions` | existing process-local Intervention Manager/operator registry | implemented and client-tested |
| Intervention detail | `human-intervention.png` | paused before control; owner/action states from backend | `/interventions/:interventionId` | existing P4.2/P4.3 operator API and H-02 context | implemented and visually verified |
| Teach | none | no reference-defined screen/state | `/teach` | none in P5.4b; P6 runtime explicitly unavailable | implemented visual shell only |
| Sessions | shell navigation only | truthful unavailable/current-session state | `/sessions` | current process session state if exposed | implemented |
| Evidence | shell navigation only | curated/local safe-event index | `/evidence` | sanitized evidence only | implemented |
| Settings | shell navigation only | nonsecret display settings only | `/settings` | public nonsecret configuration | implemented |

## Mapping decisions

- `run-detail.png` and `human-intervention.png` visibly select Home. This is recorded rather than
  corrected in the manifest. Their implementation captures preserve that reference state.
- The capability reference combines list and detail in one split view; it is one product state, not
  two competing designs. The selected capability route may deep-link while retaining the split
  composition.
- No image under the complete current directory defines a Discover page or Teach page. These are
  not unresolved references. They use the shared extracted shell/components and honest states;
  Teach controls that imply voice or screen sharing remain disabled and explicitly unconnected.
- The CoreBank/browser content shown inside references is illustrative. Runtime SurfaceView owns
  actual intervention imagery; a persisted run timeline never fabricates a live browser session.

</details>
