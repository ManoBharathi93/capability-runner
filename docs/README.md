# Documentation map

You do not need to read every file to review this project.

| Your question | Read this |
| --- | --- |
| How do I install and run it? | [Root README](../README.md) |
| What should I click and expect? | [Screenshot guide](submission/test-product.md) |
| Why was it designed this way? | [REPORT](../REPORT.md) |
| Where is the proof? | [Evidence index](../evidence/README.md) |
| What is still incomplete? | [Readiness](submission/readiness-report.md) |
| What other cases can I test? | [Manual checklist](submission/manual-test-guide.md) |
| Which code owns each part? | [Repository map](repository-map.md) |
| How do I run the evaluation? | [Evaluation guide](../evals/README.md) |

Start with setup, the screenshot guide and REPORT. The remaining pages are
references, not required reading in sequence.

## For engineering review

[System flow](submission/system-design.md) explains the request path.
[Architecture](architecture.md) and [decision records](adr/README.md) preserve
the approved boundaries. [Progress](progress.md) records completed checks.

Older plans, subsystem notes and visual records have a short introduction and
expandable detail. Their dates and old phase labels describe work at that time;
they do not override the current implementation or prove a feature works today.

The status terms have precise meanings:

- **ACCEPTED BASELINE**: an approved decision.
- **PROPOSED IMPLEMENTATION DETAIL**: an unresolved choice.
- **VERIFIED BEHAVIOR**: a completed check with evidence recorded in progress.

The repository also contains instructions for coding agents. Those govern edits;
they are not product documentation a reviewer needs to read.

## Useful words

| Word | Meaning here |
| --- | --- |
| Capability / artifact | A saved workflow with inputs, steps, outputs and checks. |
| Profile / binding | The app-specific instructions for finding a control. |
| Deterministic Replay | Following saved instructions without asking a model what to do next. |
| Allowlist | The apps or actions trusted configuration permits. |
| Handoff | A person takes the existing browser, then returns control. |
| Generation | A version of session ownership used to reject old requests. |
