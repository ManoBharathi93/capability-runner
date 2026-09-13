# Manual test checklist

Start with the [screenshot guide](test-product.md) for setup and the main flow.
This page adds negative cases and checks that require the test harness.
It covers supported behavior, not every possible website.

## Test data

All values are synthetic. Amounts below are USD minor units (cents).

| Member | State | Savings | Checking |
| --- | --- | ---: | ---: |
| `12345` | Active | 438221 | 15840 |
| `67890` | Active | 98765 | 5120 |
| `55555` | Restricted | Do not return as success | Do not return as success |
| `00000` | Missing | No account | No account |

Use 67890 for Discovery and 12345 for Replay. Member 93604 does not exist.
Account creation and checkout are not implemented.

## Discovery and Replay

Real model runs may fail. The invariant is that failure stays visible and never
produces a fabricated successful artifact. Start a new run for each Discovery case.

| ID | Input or action | Expected result |
| --- | --- | --- |
| UI-02 | Empty or whitespace-only goal. | Discover stays disabled. |
| UI-03 | More than 4,000 goal characters. | Input is bounded; an oversized request cannot start a run. |
| UI-04 | New legacy web app with an empty, relative, malformed or `file:` URL. | Disabled or rejected. |
| UI-05 | Valid URL absent from the configured read-only allowlist. | Rejected before browser execution. |
| UI-06 | CoreBank known profile: `Open member 67890 and tell me how much is in their Savings account.` | On successful Discovery: Savings, $987.65, saved capability and binding. |
| UI-07 | Replay that capability with `12345`. | SUCCESS, 438221/USD, zero model calls. |
| UI-08 | Replay with `67890`. | SUCCESS, 98765/USD, zero model calls. |
| UI-09 | Replay with `00000`. | BUSINESS_OUTCOME / MEMBER_NOT_FOUND; no balance. |
| UI-10 | Replay with `55555`. | Non-success, not MEMBER_NOT_FOUND; no successful balance. |
| UI-11 | CoreBank new-app mode: `Find the savings balance for member 67890.` | If verified, creates a capability and generated profile. No prepared target catalog. |
| UI-12 | LegacyBank B: `Find the savings balance for customer 67890.` | If verified, selects Savings and creates its own package. |
| UI-13 | Replay the Bank B savings package with `12345`. | SUCCESS, 438221/USD, zero model calls. |
| UI-14 | Bank B: `Find the checking balance for customer 67890.`; replay with `12345`. | Discovery shows $51.20; Replay returns 15840/USD with zero model calls. |
| UI-15 | New-app mode: `Delete every customer.` | Unsupported goal or safe failure; no destructive action or successful artifact. |

A generated package does not inherit unobserved business outcomes. The
MEMBER_NOT_FOUND expectation above belongs to the trusted CoreBank savings contract.

## Product pages and state

| ID | Action | Expected result |
| --- | --- | --- |
| UI-01 | Open Home, Discover, Capabilities, Runs, Interventions, Evidence, Settings and Teach. | Pages render; Teach is disabled. |
| UI-16 | Watch Discovery preview and timeline. | Images change with the managed session; structured events show progress. |
| UI-17 | Submit again while Discovery runs. | Duplicate submission prevented. |
| UI-18 | Inspect the saved capability, run and evidence pages. | Definitions and recorded outputs agree; no credentials or raw model payloads. |
| UI-19 | Finish active work, then restart the server. | Active sessions disappear; saved packages and logs remain. |

The catalog gives new-app workflows generic names. Inspect success conditions
to identify Checking. Sessions lists active **handoff** sessions; an empty list
is normal when there is no active intervention.

The process retains at most eight Discovery workspaces, including failed and
completed attempts. After finishing active work, restart to free that capacity.
Rebuilding the frontend does not reset backend state.

## Physical handoff

Follow the [five steps with screenshots](test-product.md#5-physically-take-over-the-existing-browser).
Use a local desktop with `CAPABILITY_RUNNER_BROWSER_HEADLESS=false`.

Expect the same browser session, human ownership at generation 2, and SUCCESS
with 98765/USD at generation 3 after opening Savings and returning control.
The earlier three automated actions must not repeat. The completed browser closes.

Record the run ID, visible window, physical action, output and generation.
Automated Playwright input and the CLI handoff do not prove physical acceptance.

Start a fresh handoff for each negative case:

| ID | Action | Expected result |
| --- | --- | --- |
| HITL-01 | Take control, then return without acting. | VALIDATION_FAILED; no balance. |
| HITL-02 | Open Checking instead of Savings. | Wrong-account validation fails; no success output. |
| HITL-03 | Close the managed browser, then return. | BROWSER_SESSION_CLOSED; no replacement browser. |
| HITL-04 | Return twice or double-click. | At most one continuation; duplicate rejected. |
| HITL-05 | Stop before or after taking control. | Session ends without resumed success. |
| HITL-06 | Restart during handoff. | Active ownership is lost; saved evidence remains. |
| HITL-07 | Use headless mode. | No physical browser window; UI explains the limitation. |

If you see the old **Return Control to Agent** label, hard-refresh the product.
If the managed window is gone, stop that attempt and start a new handoff.

## CLI and evaluation

See [CLI commands](demo-entrypoints.md) for Discovery/Replay, not-found and
controlled handoff. See [evaluation](../../evals/README.md) for the 13-case suite.
Both preserve failed attempts; a safe negative result is not a discovered capability.

Some states need deliberate fixture changes, so use these tests:

```powershell
uv run pytest tests/integration/surfaces/test_generic_browser.py -q
uv run pytest tests/integration/capabilities/test_generic_package.py -q
uv run pytest tests/integration/replay/test_replay_engine_browser.py -q
uv run pytest tests/integration/interaction/test_action_gateway_browser.py -q
uv run pytest tests/end_to_end/test_direct_browser_handoff.py tests/end_to_end/test_replay_intervention_resume.py -q
```

They check duplicate/hidden controls, stale references, package integrity,
wrong entity, expiry, slow responses, policy denial, uncertain effects,
ownership and continuation. These are harness tests, not extra product UI scenarios.

For the full local check:

```powershell
uv run pytest -q
uv run ruff check .
uv run pyright
uv lock --check
npm --prefix web test
npm --prefix web run typecheck
npm --prefix web run build
```

[Progress](../progress.md) records the latest completed results: 380 ordinary
Python tests in the full run. The sign-in change passed 38 focused Python tests
and 12 frontend tests. Eight live cases are excluded by default.

## Optional browser scripts

Build the frontend first. Discovery scripts need the running product and a provider:

```powershell
uv run python scripts/verify_discovery_workspace.py --application corebank-known
uv run python scripts/verify_discovery_workspace.py --application bank-b --product checking
```

Run them one at a time. The isolated handoff script needs neither a model nor an
existing product server:

```powershell
uv run python scripts/verify_workspace_handoff.py --headed
```

It supplies automated input, captures screenshots, and may update screenshot
files. Review those changes before committing; they are not physical acceptance.
