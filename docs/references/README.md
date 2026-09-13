# Capability Runner — Design References

These are design concepts, not screenshots proving the product works. Use them for appearance only. For implemented behavior, open the screenshot testing guide.

See [the screenshot guide](../submission/test-product.md) and
[progress](../progress.md) for the reviewer path and current evidence.

<details>
<summary>Detailed visual record</summary>

These are 12 generated concept images from the design conversation, not screenshots
of implemented software and not execution evidence. All displayed names, metrics,
capability lists, statuses, logs, dates and security claims are illustrative.

## How to use this folder

- `architecture/`: original generated concept diagrams. Use for visual hierarchy;
  do not copy every arrow or statement as a technical contract.
- `ui/current/`: the latest general product visual direction. Use navy, blue,
  light surfaces, spacing and navigation as references; behavior follows the
  written UI specification. "Current" means visual reference, not shipped UI.
- `ui/future/`: optional post-core teaching draft-review inspiration. No automatic
  approval, successful test, or reliable extraction is implied by the illustration.
- `ui/archive/`: superseded dense dashboards, collage and pre-Teams teaching
  concepts. Do not use these as the active teaching-screen specification.

The final chat-first / Teams-like teaching-call UI has NOT been supplied as a
matching finished image in this pack. Define its behavior in `docs/ui-spec.md`.
The final natural-language Discover form also needs its written specification;
"Discover" must not just link to the existing capability catalog.

## Source precedence

The original assignment defines submission requirements. Accepted written
architecture/ADRs and the latest owner UI requirements define implementation
choices. Images provide visual references only. Report unresolved conflicts;
do not silently treat an image as permission to change accepted behavior.

Store corrected, editable technical diagrams separately under `docs/architecture/`
(e.g. Mermaid source and reviewed exports). Do not overwrite these originals and
present them as technically validated.

## Known technical inaccuracies in these concept images

1. Discovery is a genuine LLM-driven observe/decide/act loop. "Learns from user
   actions" describes the optional human-teaching path, not mandatory discovery.
2. Only the Model Client connects to the LLM provider. The Browser Surface Adapter
   operates the target application; it does not call the LLM.
3. State Evaluator checks declared conditions and outputs; the engines choose
   actions/transitions. The evaluator is model-free and does not dispatch clicks.
4. Structural validation does not mean automatic approval, behavioral correctness,
   unattended permission, or production readiness. Record validation, testing and
   any explicitly implemented approval as separate states.
5. Intervention is conditional, not a mandatory step on every successful run.
   It applies during discovery and replay and must preserve the same live session.
6. Discovery and replay both use policy, session-ownership enforcement and the
   shared Action Gateway. Evidence is emitted throughout, not only at the end.
7. "Production ready", "Compliant", "Complete audit trail", "at scale" and
   reliability metrics are unsupported concept copy, not implementation claims.
8. Legacy-bank operations in this assignment use UI automation, not the bank's
   business API. API badges in old library mockups must not misrepresent this.

## Repository placement

Merge this `docs/references/` tree into the project root after checking for name
conflicts. Preserve existing repository documentation rather than overwriting it.
Do not place these mockups in `/evidence/`. That directory is for real, sanitized
execution evidence. Do not place entire mockups in the frontend public assets
folder or present a screenshot as a working interface.

No company assignment document, hosted-model endpoint, credential, or real run
record is included in this archive. Review images and publication permissions
before committing to a public repository.

## Image inventory

- `architecture/data-flow-concept.png` (original: `capability_runner_data_flow_diagram.png`)
- `architecture/layered-concept.png` (original: `capability_runner_layered_system_view.png`)
- `architecture/system-concept.png` (original: `capability_runner_enterprise_architecture.png`)
- `ui/current/home.png` (original: `capability_runner_saas_dashboard.png`)
- `ui/current/capability-library.png` (original: `capability_runner_dashboard.png`)
- `ui/current/run-detail.png` (original: `capability_runner_corebank_automation_dashboard.png`)
- `ui/current/human-intervention.png` (original: `capability_runner_human_intervention_dashboard.png`)
- `ui/future/teaching-draft-review.png` (original: `capability_runner_draft_review_dashboard.png`)
- `ui/archive/dense-dashboard.png` (original: `capability_runner_automation_dashboard.png`)
- `ui/archive/multi-screen-collage.png` (original: `a_clean_infographic_dashboard_collage_on_a_white_b.png`)
- `ui/archive/teaching-setup-form.png` (original: `teach_a_capability_dashboard.png`)
- `ui/archive/teaching-live-pre-teams.png` (original: `live_teaching_session_dashboard.png`)

</details>
