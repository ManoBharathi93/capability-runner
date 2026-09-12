# Requirements

## Status and precedence

This document summarizes the supplied interface.ai assignment and the owner-authorized phase plan. The local `Assignment.md` remains the source for assignment wording. Accepted architecture and ADRs govern implementation choices; this summary does not introduce new product scope.

P1.0 implements repository readiness only. All product behavior below remains planned unless `docs/progress.md` records implementation and completed evidence separately.

## Required end-to-end behavior

| ID | Requirement | Required evidence before completion |
| --- | --- | --- |
| R-01 | Accept a natural-language goal and trusted target application/profile. | A real invocation record with sanitized inputs. |
| R-02 | Run a bounded LLM-driven observe-decide-act loop against a live UI. | At least one genuine provider-backed discovery log and richer approved evidence. |
| R-03 | Convert a successful run into a typed, versioned, reviewable JSON capability with inputs, outputs, ordered actions, targets, and a checkpoint. | Saved generated artifact plus schema/semantic validation results. |
| R-04 | Replay the saved capability without model decisions, resolve stable targets, verify success, and return typed outputs. | Replay with model access absent and fresh application data. |
| R-05 | Distinguish success, known business outcomes, recoverable conditions, and hard failures. | Tests and run evidence covering each supported category. |
| R-06 | Enforce explicit target/route and action allowlists and conservatively handle risky or irreversible actions. | Allowed, denied, unknown, malformed, and approval-path tests. |
| R-07 | Avoid persisting credentials, tokens, or raw sensitive data in artifacts and evidence. | Synthetic canary scans of supported evidence channels; no universal screenshot-redaction claim. |
| R-08 | Produce structured evidence and an approved richer failure signal. | Sanitized JSONL plus a reviewed screenshot, snapshot, or trace from a real failure. |
| R-09 | Detect blocked/stuck states, route intervention, transfer control of the same live session, record human actions, and validate handback. | Correlated same-session takeover/resume evidence. |
| R-10 | Preserve an abstraction path for legacy browser and desktop surfaces. | Contract/conformance rationale and tests; implementation beyond browser is not required. |
| R-11 | Represent vendor-product reuse and safe tenant/version specialization without silent drift repair. | Design plus representative variant tests; production multi-tenancy is not required. |

## Required interfaces and deliverables

- A command interface and thin web interface invoke the same Python backend core.
- The React and TypeScript client renders backend state and does not become another workflow engine.
- A public repository eventually includes setup and exact discovery/replay demo commands in `README.md`.
- Final `REPORT.md` uses exactly: Architecture; Artifact schema; Determinism & error handling; Heterogeneity & multi-tenant; Escalation & handoff; Safety; Cuts.
- Final `evidence/` includes a generated capability plus discovery and replay logs, ideally including an exceptional replay.
- A genuine LLM-driven live-surface discovery is mandatory; a hand-authored fixture cannot satisfy it.

## Safety and data constraints

- Use synthetic data and a local/demo/sandbox target that may be automated lawfully.
- Route discovery, replay, and human surface actions through Action Gateway.
- Deny unknown or ambiguous actions and targets by default.
- Keep real secrets out of source, artifacts, logs, screenshots, URLs, and prompts wherever avoidable.
- Keep raw runtime evidence in ignored local storage; curate only reviewed and sanitized real evidence into `evidence/`.
- Treat external-provider retention separately from local deletion and make no promise the system cannot enforce.

## Scope constraints

- Use the accepted modular monolith and named components; do not add distributed infrastructure for appearance.
- Implement a thin complete vertical slice before optional breadth.
- Desktop and production multi-tenant infrastructure are design concerns, not required implementations.
- Teams-like voice-and-screen teaching is P6-only and requires core acceptance plus explicit owner authorization.
- P1.0 must not implement contracts, engines, adapters, interfaces, frontend application code, or the demo target beyond package/directory foundations and executable repository checks.