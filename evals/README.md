# Evaluate Discovery and Replay

Use these commands without a model key:

```powershell
uv run capability-runner eval discovery --suite evals/banking.yaml
uv run capability-runner eval replay --suite evals/banking.yaml
```

Both prepare a capability through Discovery and run it in a fresh Replay browser.
The phase marks the evaluation focus. Preparation calls and Replay calls are
counted separately; Replay must add zero.

## What the 13 cases check

The suite covers savings paraphrases, new-app savings, Checking, an unsupported
destructive goal, page injection, wrong member, expiry and MEMBER_NOT_FOUND.

Each case declares the expected result, output, allowed/forbidden actions and
execution bounds. Ordinary evaluation uses scripted model fixtures and local
banking apps. It tests integration; it does not prove real-model reliability.

A safe failure can pass a negative case. **Thirteen passing cases do not mean
thirteen successfully discovered capabilities.**

## Use a real provider

With [provider configuration](../docs/providers.md), opt in explicitly:

```powershell
uv run capability-runner eval discovery --suite evals/banking-live.yaml --live
```

Failures stay in the report. Successful cases must save a valid package and
produce a matching model-free Replay.

## Read the report

Results are written incrementally to `var/evals/<run-id>/report.json`.
Inspect classification, expected versus actual output, action counts and Replay
model calls. Local reports are not automatically published as curated evidence.

The suite files use JSON syntax, a valid YAML subset. The strict loader accepts
that subset without another parsing dependency.

For stale controls, ownership and uncertain-effect tests, use the
[manual checklist's harness commands](../docs/submission/manual-test-guide.md#cli-and-evaluation).
Recorded results are in [progress](../docs/progress.md).
