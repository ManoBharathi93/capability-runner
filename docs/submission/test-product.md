# Test the product, step by step

This is the shortest path through the assignment: **goal → real Discovery → saved
capability → model-free Replay → expected error → human takeover → evidence**.
Allow 10–15 minutes for a first run, including provider waits. All members and
balances below are synthetic. For more cases, use the [full manual checklist](manual-test-guide.md).
For recording, use the [3–5 minute demo script](demo-walkthrough.md).

## 1. Start it

From the repository root:

```powershell
uv sync --all-groups
uv run playwright install chromium
npm --prefix web ci
npm --prefix web run build
$env:CAPABILITY_RUNNER_BROWSER_HEADLESS = "false"
uv run capability-runner serve
```

Open **http://127.0.0.1:5000**. Discovery needs one configured provider in your local
`.env`; see [provider setup](../../README.md#provider-configuration). Replay and the
handoff demo need no model key. Never display `.env` in your recording.

Use a local desktop for human takeover. A headless server cannot display the
managed browser to you. Keep the product running; restarting loses active sessions.

## 2. Discover a savings lookup and inspect its artifact

Open **Discover**, select **CoreBank Legacy · known profile**, and submit:

```text
Open member 67890 and tell me how much is in their Savings account.
```

Expect changing live imagery, Discovery lifecycle events, a Savings account screen
with **$987.65 USD**, and **Capability created**. Open the typed capability and
application-binding details below it. Check that the member is an input parameter,
the balance and currency are outputs, and actions have conditions.

![Successful savings Discovery and generated artifact](screenshots/savings-discovery.png)

The image is from a real provider run. If your provider fails, the product must
show non-success; do not expect identical timing or every model attempt to succeed.

## 3. Replay with a different input

Click **Replay with new input**, enter **12345**, then **Run Replay**.
Expect **SUCCESS**, **438221** minor units (**$4,382.21**), **USD**, and
**Replay model calls 0**. The Discovery preview still shows the original member;
the separate Replay result reports the new input's output.

![Different-input savings Replay with zero model calls](screenshots/savings-replay.png)

Now replay with **00000**. Expect **BUSINESS_OUTCOME / MEMBER_NOT_FOUND**,
zero model calls, and no balance. That is a known business result, not an automation
crash or a successful balance lookup.

![Member-not-found business outcome](screenshots/member-not-found.png)

## 4. Verify a different banking outcome and interface

Start a new Discovery using **LegacyBank B · new-app discovery**:

```text
Find the checking balance for customer 67890.
```

Expect Checking and **$51.20 USD**. Then replay with **12345** and expect
**15840** minor units (**$158.40**), **USD**, and **Replay model calls 0**.
This interface has different forms and tables and produces its own bindings.

![Checking Replay on LegacyBank B](screenshots/checking-replay.png)

Savings and checking are supported outcomes. Creating accounts is not implemented.
Member **93604** is not a fixture. A request to create an account must not produce
a successful lookup artifact. This does not demonstrate one identical capability
reused across two tenant profiles; that remains future work.

## 5. Physically take over the existing browser

1. Open **Interventions → Start Demo Handoff**. This model-free fixture runs the
   three initial member-search actions and pauses before opening Savings.
2. Click **Take control**. Expect **Human reviewer**, **generation 2**, and the
   existing browser window to come forward. If it does not, use **Focus live
   browser** or your OS task switcher. The screenshot in the product is a preview.
3. In the **managed Chromium window**, physically click **Open** in the **Savings**
   row. Do not use your personal browser or create another tab.
4. Confirm **Savings Account**, member **67890**, and **$987.65 USD** in that window.
5. Return to the product and click **Return control to automation**. Stop interacting
   with the managed window. Expect **SUCCESS**, **generation 3**, and the same
   surface session ID. The browser closes after completion.

![Human ownership and preview-only product controls](screenshots/handoff-human.png)

![The same managed browser after opening Savings](screenshots/managed-browser-after.png)

![Fresh validation and successful continuation](screenshots/handoff-completed.png)

During takeover, **Sessions** links to this intervention and shows application,
surface ID, controller, state and generation. After completion it is empty again.
See [Sessions during takeover](screenshots/sessions-human.png).

These handoff screenshots were captured using automated Playwright input into the
actual retained Page in headed mode. They **do not prove physical human acceptance**.
Perform the five steps yourself and record the run ID and result for that gate.
The [recorded automated check](../../evidence/direct-browser/ui-check.json) explicitly
retains this distinction.

## 6. Check failure handling and evidence

Start a fresh handoff for each case:

| Your action | Expected result |
| --- | --- |
| Take control, then return without clicking anything | Validation fails; no success or balance. |
| Open Checking instead of Savings, then return | Wrong-account state rejected; no success output. |
| Close the managed window, then return | `BROWSER_SESSION_CLOSED`; no replacement browser. |
| Click Stop | Session ends without a resumed success. |
| Return again after completion | Inactive or stale request rejected; no second execution. |

Use **Evidence** and the run's recorded events. For native handoff, look for
`INTERVENTION_REQUESTED`, `AUTOMATION_QUIESCED`, `HUMAN_CONTROL_GRANTED`, observed
`HUMAN_BROWSER_ACTION` events, `HUMAN_CONTROL_RETURNED`, `RESUME_VALIDATION`, and
`AUTOMATION_CONTROL_RESTORED` only after valid handback. Human observations carry
`actor=human` and `source=direct_browser_interaction`; they are not gateway executions.
Capture is best effort and stores no values or keystrokes. Final fresh state determines success.

| Assignment concern | Where to inspect |
| --- | --- |
| Natural-language goal and real model Discovery | Step 2; [curated Discovery evidence](../../evidence/through-line/evidence.jsonl) |
| Parameterized artifact, output contract and conditions | Step 2; [saved JSON](../../evidence/through-line/capabilities/lookup_savings_balance/1.0.0.json) |
| Deterministic Replay and business outcomes | Step 3 and its screenshots |
| Legacy interface support | Step 4; [checking evidence](../../evidence/checking/ui-summary.json) |
| Ownership, takeover and safe return | Steps 5–6; [direct-browser evidence](../../evidence/direct-browser/evidence.jsonl) |
| Policy denial, stale dispatch, uncertainty, privacy and quiescence | [Full checklist and focused commands](manual-test-guide.md#supported-edge-cases-through-focused-tests); these are harness checks, not screenshot claims |
| Tenant reuse, desktop seam, cuts and engineering decisions | [REPORT](../../REPORT.md); not claimed implemented by these screenshots |

The guide's images are reviewed synthetic application captures, not mockups.
[Screenshot provenance](screenshots/README.md) identifies their runs. Current
regression results are in [progress](../progress.md). Voice, Teach, screen sharing,
production authentication, and universal screenshot/PII redaction are not implemented.
