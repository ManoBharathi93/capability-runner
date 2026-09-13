# Reviewer video walkthrough

This script is designed for an eight-to-ten-minute recording. Use your own voice and pacing; the quoted lines are prompts, not text that must be read word for word.

## Before recording

Build and start the product with `uv run capability-runner serve`. Configure the provider in `.env`, but never open that file on camera. Keep these tabs ready:

- `http://127.0.0.1:5000/discover`
- `/capabilities`
- `/runs`
- `/interventions`
- `/evidence`
- the repository in your editor, with `README.md`, `REPORT.md`, `src/capability_runner`, `web`, `demo_app`, `evals`, `evidence`, and `tests` visible

Do one private rehearsal. Real model latency and availability vary. If a live Discovery fails during the recording, show the structured failure honestly, explain that no capability was published, and use a separate successful run already retained by the local product to continue the architecture walkthrough. Do not splice a failure into an apparent success.

## 0:00-0:40 - The problem and result

Show the Discover page.

> Legacy banking applications often contain valuable workflows but no usable API. Capability Runner uses a model once to discover a bounded workflow in a real browser, turns the verified trace into a typed capability and a separate application binding, and then replays it deterministically without a model in the execution loop.

Point to Discover, Capabilities, Runs, Interventions, and Evidence in the navigation.

> This is a working local product surface backed by the same runtime as the CLI. I will show the live browser flow, the generated package, a different-input replay, a business outcome, and a same-session human handoff.

## 0:40-1:50 - Repository overview

Switch to the repository tree. Keep this short and connect each directory to one responsibility.

> The Python package under `src/capability_runner` contains the contracts and runtime boundaries. Discovery is the only path allowed to call a model. Capability building and validation turn verified behavior into versioned data. Replay interprets that data without a model. Every browser or operator action passes through Action Gateway, which applies policy and session ownership before the browser adapter acts.

> `web` is the React reviewer interface. `demo_app` contains the product server and two synthetic banking applications. `evals` contains the normal and explicitly live qualification suites. `tests` covers contracts, browser integration, Replay, policy, and handoff concurrency. `evidence` is the small curated record from actual executions; ordinary run output stays under ignored `var`. `REPORT.md` explains the decisions and the limits without claiming unimplemented production features.

Open the top of `REPORT.md` or a simple architecture diagram if desired.

> I kept this as a modular monolith because control over one browser session matters more here than service distribution. The key invariant is that model output never becomes browser code or a selector. It is parsed as a bounded decision, resolved against current visible state, checked by policy, and then dispatched.

## 1:50-3:25 - Live Discovery

Return to `/discover`. Select **CoreBank Legacy - known profile** and enter:

```text
Open member 67890 and tell me how much is in their Savings account.
```

Click **Discover Capability**.

> This sentence is the goal; it is not a script. Discovery needs an LLM because mapping language to an unfamiliar current interface is open-ended. The model receives a bounded observation and can choose only from the allowed decision schema.

As the run advances, point to the managed browser preview and structured timeline.

> The imagery is from the same managed browser session that the agent operates. Actions are recorded as typed events. Hidden controls, ambiguous matches, stale references, a wrong member, or unsupported actions produce non-success. In banking, conservative failure is safer than a plausible but incorrect success: a refusal can be investigated, while another member's balance could be trusted and acted on.

On success, show member `67890`, Savings, and `$987.65`. If the provider fails, show the error and use a retained successful run for the next section.

## 3:25-4:25 - Capability and binding

Expand or open the generated capability and its application binding.

> The capability is versioned JSON, not generated automation code. It defines typed inputs and outputs, ordered semantic steps, success conditions, known business outcomes, and narrow retry rules.

Point to a semantic target and then its separate binding.

> Workflow meaning is separate from application resolution. A semantic instruction such as open Savings should stay understandable when labels or markup change, while the application profile owns the concrete way to find that target. This separation supports tenant-specific bindings and drift checks. The current evidence does not claim that one byte-identical capability has already been reused across two tenants.

> Uncertain side effects are never retried automatically. If a click may have succeeded but confirmation was lost, repeating it could duplicate a financial operation. Replay returns an explicit failure instead of guessing.

## 4:25-5:20 - Fresh, model-free Replay

In **Replay with another input**, enter `12345` and run it.

> I discovered with member 67890 and I am replaying with a different input, 12345. Replay loads and validates the saved artifact, checks current application identity and member identity, resolves each semantic target, and evaluates fresh state. It intentionally has no model fallback.

Show `SUCCESS`, `balance_minor_units = 438221`, `currency = USD`, and **Replay model calls 0**.

> The integer is the balance in minor units, so this is $4,382.21. Zero model calls is an enforced dependency boundary, not just a prompt choice. It makes repeated execution reproducible, cheaper, and auditable.

## 5:20-5:55 - Expected business outcome

Replay with `00000`.

> A missing member is an expected banking outcome, not a crashed browser. The trusted CoreBank capability declares `MEMBER_NOT_FOUND`, so Replay returns `BUSINESS_OUTCOME` with no fabricated balance and still uses zero model calls.

Point out that a restricted or contradictory state would instead fail conservatively; it must not be collapsed into member-not-found.

## 5:55-7:05 - A previously unprofiled application

Start a fresh Discovery workspace. Select **LegacyBank B - new-app discovery** and enter:

```text
Find the savings balance for customer 67890.
```

> LegacyBank B has a different enquiry form, labels, navigation, and portfolio table. This mode begins without a hand-authored semantic target catalog. Discovery uses short-lived references to current visible elements; only uniquely resolved, verified observations can become durable bindings.

On a successful run, show the generated profile and replay with `12345`, highlighting `438221 / USD` and zero model calls.

> This proves bounded profile-less Discovery on a second web UI and successful Replay from its generated package. It does not prove universal website automation or cross-tenant reuse of one identical capability.

If time or provider variability makes this live step unreliable, show the retained successful product run and then open the corresponding dated evidence in `docs/progress.md`. State clearly that it is a prior recorded run.

## 7:05-8:10 - Same-session human handoff

For an additional banking outcome before handoff, use LegacyBank B with
`Find the checking balance for customer 67890.` Replay with `12345` and show `15840 / USD` and
zero model calls. Explain that savings and checking have different fixed expected balances; a
valid-looking savings value must never pass a checking request. This adds roughly a minute.

Interventions is directly accessible in the sidebar. Sessions shows active handoffs and provides
**Open Interventions** and **Refresh sessions**; an empty list before starting a handoff is expected.

Open `/interventions`, click **Start Demo Handoff**, open the live item, and click **Take Control**. Use **Savings** once and then click **Return Control to Agent**.

> This capability pauses before an approval-required action. The operator receives control of the same managed session and can use only trusted semantic controls. Operator actions still pass through Action Gateway.

As it completes, show the final `98765 / USD` result.

> Handback never resumes from stale assumptions. Capability Runner re-observes the page, verifies that the operator completed the blocked step, advances the session generation, and resumes once without repeating the action. The final Replay still makes zero model calls.

## 8:10-9:05 - Evaluation and evidence

Open a terminal showing the previously completed normal evaluation or run it before recording:

```powershell
uv run capability-runner eval replay --suite evals/banking.yaml
```

> The deterministic suite contains 13 cases: paraphrases, two application structures, savings and checking, destructive intent, prompt-injection-like content, wrong identity, an expired session, and member-not-found. The recorded baseline passed all 13, including nine matching fresh replays, three generated profiles, zero false successes, zero wrong-entity successes, zero unsafe actions, and zero Replay model calls.

Open `/evidence` or the curated `evidence` directory.

> Evidence is intentionally minimized. It keeps correlation, classifications, fingerprints, and reason codes while excluding provider credentials, raw model payloads, selectors, raw DOM, and invocation values. Live browser frames are not persisted.

## 9:05-9:45 - Honest limits and close

End on the product or `REPORT.md`.

> The implemented scope is an allowlisted, read-only Playwright browser adapter with local JSON storage and process-local sessions. The local operator surface has no production authentication. Redaction is key- and exact-value-based, not universal screenshot or PII detection. Voice, screen sharing, desktop automation, distributed recovery, and formal capability approval workflow are future work.

> The completed result is the core engineering claim: one genuine model-guided Discovery can produce a reviewable typed package, and that package can execute against fresh state and different inputs without putting a model back into Replay.

Pause briefly on the GitHub repository URL and the README setup commands so a reviewer can reproduce the demo.
