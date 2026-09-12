# Discovery and Replay evaluation

`banking.yaml` and `banking-live.yaml` use JSON syntax, which is valid YAML. The strict Pydantic
loader intentionally accepts this subset without adding a YAML dependency. Each case declares
application, goal, setup, expected classification/outputs/business outcome, allowed/forbidden
actions, bounds and whether a profile exists before Discovery.

The two real applications support customer/member lookup, account category/state, savings and
checking balances. CoreBank additionally has a trusted MEMBER_NOT_FOUND business-outcome contract.
The suite exercises five savings paraphrases, unprofiled savings, checking, unsupported goals,
injection, wrong entity, expiry and the known business outcome. Scripted models live in the
explicit evaluation fixture module; production Discovery contains no application branches.

```sh
uv run capability-runner eval discovery --suite evals/banking.yaml
uv run capability-runner eval replay --suite evals/banking.yaml
uv run capability-runner eval discovery --suite evals/banking-live.yaml --live
```

Both commands prepare a capability through Discovery and then load it for a fresh browser Replay.
The `phase` field identifies the requested evaluation focus. Model calls used in preparation are
reported separately; Replay must add zero. Normal runs use scripted fixtures and loopback HTTP,
with no external network/model call. Only `--live` with the live suite uses a configured provider.
No pre-existing profile is constructed for LegacyBank B.

The browser/session safety cases also run in ordinary pytest: duplicate and hidden controls plus
stale ephemeral refs in `tests/integration/surfaces/test_generic_browser.py`; injection, policy
denial, wrong identity and application mismatch in `tests/integration/capabilities/test_generic_package.py`;
stale generation and unknown side-effect/no-retry behavior in the existing interaction and Replay
tests. These focused protocol tests complement the 13 workflow cases; they are not additional
successful discoveries in the evaluation report.

Reports are written incrementally to `var/evals/<run-id>/report.json` and preserve failed attempts.
Metrics derive from actual results, validated artifacts and gateway evidence. A matching expected
safe failure is a passed test case; it is not a successfully discovered capability. Provider
availability and nondeterministic model failures remain visible. Reports are local runtime data
and are not automatically copied into submission evidence.
