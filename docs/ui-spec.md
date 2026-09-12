# Product UI Specification

## Status

The React and TypeScript frontend is an **ACCEPTED BASELINE** product interface. It is deferred to optional P5.4 polish and is not implemented. Written behavior and architecture take precedence over generated concept images in `docs/references/`.

## Visual direction

Use a navy, white, and blue foundation with restrained semantic status colors, generous spacing, and progressive disclosure. The current reference images guide visual hierarchy only; displayed data, metrics, success claims, routes, and security copy are illustrative.

## Discover

- **Route:** `/discover`.
- **Input:** a natural-language outcome plus a trusted target application/profile.
- **Primary action:** Start discovery.
- Advanced settings are collapsed by default.
- The goal describes the desired outcome, not selectors or a prescribed click sequence.
- Discovery status and observations come from the shared backend core through the thin web interface.

## Run

- The user selects an existing capability/version and supplies its typed parameters.
- Execution uses Replay Engine without model decisions.
- The view distinguishes success, known business outcome, recoverable progress, intervention, and hard failure.
- Exact route naming is a P5.4 private UI detail unless it becomes part of an external contract.

## Capability library and detail

- Show identity, version, callable inputs/outputs, steps, checkpoints, compatibility, validation state, and real replay evidence when available.
- Structural validation, approval, replay success, and readiness are separate statuses.
- Never render illustrative reference metrics as actual system state.

## Intervention

- Present the run/capability, current step, reason for stopping, approved state evidence, and current control owner.
- Taking control must bind to the existing authorized managed session; opening an arbitrary tab or showing a video stream is not control.
- Human actions use Action Gateway and are captured with sanitized human provenance.
- Handback is explicit and requires state revalidation before automation resumes.
- Detached views must connect to the same managed session and obey the same authentication, authorization, and freshness checks.

## Evidence

- Render only backend-approved sanitized event fields and attachments.
- Do not expose provider secrets, raw credentials, browser storage, or unreviewed traces.
- UI text must not promise complete redaction, compliance, audit completeness, reliability, or production readiness without evidence.

## Teach: P6 only

Teaching is a Teams-like, chat-first call experience rather than a large setup form. A user calls the assistant, explains the task, shares a selected screen, and teaches through voice and actions. Draft creation follows the call; review and successful replay testing precede readiness for supported use.

Teaching reuses Capability Validator, Capability Store, Policy Guard, Action Gateway, Session Controller, Replay Engine, and evidence controls. It does not create a second workflow engine or artifact language. Voice, media handling, and temporary teaching storage require explicit P6 authorization after core acceptance.

Temporary local conversation/media deletion and external-provider retention are separate concerns. The product must not promise deletion beyond what it can enforce.