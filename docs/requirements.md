# What the assignment requires

Build one complete thread: **goal → real model Discovery → saved artifact →
model-free Replay → human takeover → evidence**.

The banking and shopping goals are alternatives. Three unrelated business
workflows are not required. The owner selected savings, checking and handoff
within the existing sandbox.

## Required behavior

| ID | Requirement in plain language | Proof needed |
| --- | --- | --- |
| R-01 | Accept a natural-language goal and target app. | A real invocation. |
| R-02 | Use an LLM to observe and act on a live UI. | Real-provider run evidence, not only a scripted model. |
| R-03 | Save a typed, versioned capability. | Inputs, outputs, steps, targets and success conditions. |
| R-04 | Run the saved artifact without a model. | Fresh Replay with another input and verified outputs. |
| R-05 | Separate success, business outcomes and failures. | Positive and negative tests with clear reasons. |
| R-06 | Enforce configured scope and safe actions. | Allowed, denied, unknown and approval cases. |
| R-07 | Keep secrets and sensitive values out of persisted records. | Redaction tests and explicit limits. |
| R-08 | Record useful run evidence and failure context. | Structured logs and bounded richer evidence. |
| R-09 | Let a human take the same live session and return it safely. | Ownership, human-action context and fresh resume validation. |
| R-10 | Explain how other surfaces could fit. | A credible adapter contract; desktop implementation is not required. |
| R-11 | Explain reuse across app variants or tenants. | Separate bindings and safe compatibility checks; production multi-tenancy is not required. |

The original local assignment is the source for wording. This summary does not
create extra hiring requirements. The React frontend is an owner-approved product
choice, not a mandatory framework named by the assignment.

## Deliverables

- Public source and root [README](../README.md) with setup and exact demo commands.
- Root [REPORT](../REPORT.md), about 1–3 pages, with the seven required headings.
- [Evidence](../evidence/README.md): artifact plus Discovery and Replay logs.
- Clear cuts and next work. A video is optional.

## Engineering constraints

Use the accepted single-process architecture. Replay stays independent of the
model. Every automated surface action uses Action Gateway. The owner-approved
native handoff lets physical human input act directly in the retained browser;
it does not claim gateway enforcement of those clicks.

Use synthetic data, deny unknown actions, minimize persisted values, and curate
evidence before publication. Do not promise general PII removal or provider-side
deletion.

[Readiness](submission/readiness-report.md) describes current gaps.
[Progress](progress.md) records **VERIFIED BEHAVIOR** separately from
**ACCEPTED BASELINE** decisions and **PROPOSED IMPLEMENTATION DETAIL** choices.
Older phase records are history, not a new restriction on work already authorized.
