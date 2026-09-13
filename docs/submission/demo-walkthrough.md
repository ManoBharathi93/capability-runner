# Reviewer video walkthrough

Aim for 3–5 minutes, excluding model wait time. Rehearse with the
[screenshot test guide](test-product.md). Configure your provider before recording,
keep .env off camera, and start the product with
`CAPABILITY_RUNNER_BROWSER_HEADLESS=false`. Keep your editor, Discover, and
Interventions ready. Use synthetic members only.

## 0:00–0:35 — Problem and repository

Show README and the top-level folders.

> “This project gives an agent a way to operate a banking application that has no
> integration API. The model discovers a workflow once, then a saved capability
> runs deterministically with new inputs. I concentrated on correct outcomes and
> safe handoff within two synthetic banking interfaces.”

Point briefly to `src/capability_runner` for the engines and enforcement,
`demo_app` for the targets and product composition, `web` for the client,
`tests` and `evals` for checks, and `evidence` for recorded runs.
Open REPORT only to show where the engineering decisions are explained.

## 0:35–1:35 — Discover and inspect the artifact

In Discover select **CoreBank Legacy · known profile**. Submit:

```text
Open member 67890 and tell me how much is in their Savings account.
```

> “Discovery uses a real model to propose the next action. The browser view is
> the session it is actually using. The gateway validates automated actions;
> page text and the model cannot grant permission.”

Wait for success and `$987.65 USD`. Open the capability and binding details.

> “The artifact is typed JSON with parameters, steps, conditions, outputs and
> known outcomes. Workflow meaning and application bindings are separate, so
> application-specific selectors do not become the business procedure.”

If model latency is long, make an explicit cut labelled “waiting for provider.”
If the attempt fails, show its failure and identify any earlier successful evidence
you use next. Do not present an edited sequence as one successful run.

## 1:35–2:20 — Replay and conservative outcomes

Choose **Replay with new input**, enter `12345`, and run it.
Show `438221 / USD` and **Replay model calls 0**. Then replay with `00000`
and show `MEMBER_NOT_FOUND`, with no balance output.

> “Replay deliberately has no model decisions. It loads the saved procedure,
> resolves targets, and checks fresh member and account state. False success is
> worse than refusing: a convincing wrong balance can be acted on. A known
> missing member is a business outcome, not a made-up successful result.”

Optional checking evidence: show the [checking run](../../evidence/checking/ui-summary.json).
Its different-input Replay returns `15840 / USD`. Say that this is a separate
banking outcome discovered on LegacyBank B, not account creation or proof of
reusing one identical capability across tenants.

## 2:20–3:45 — Physically take over the browser

Open **Interventions → Start Demo Handoff**. Point to the paused state.
Click **Take control**; show generation 2 and Human reviewer.

> “Automation filled the member ID, searched, and opened the member once.
> It stopped before the approval-required Savings action. Taking control
> quiesces automation and gives me this same browser.”

Switch visibly to the **existing managed Chromium window**. Click **Open** in
the **Savings** row yourself. Show Savings and `$987.65 USD`.
Return to the product and click **Return control to automation**.

> “That was my click in the application, not a proxy button or another automated
> gateway action. The product image is only a preview. Passive evidence records
> action kinds without field values or keystrokes.”

Show SUCCESS and generation 3.

> “Handback re-observes this same page before resuming. It checks that the blocked
> step is actually complete. It does not repeat my action or the three earlier
> steps, and Replay still makes no model calls. If an effect is uncertain, retrying
> it could duplicate an operation, so the system fails conservatively.”

Only use this narration if you physically performed the action. The verification
script uses Playwright as a stand-in and must be labelled as automated evidence.

## 3:45–4:45 — Evidence and limits

Open the run's evidence and the Sessions page. The completed browser is closed
and no longer appears among active handoffs. Point to the stable surface ID,
human observation source, fresh validation, and recorded outcome.

> “Tests also return without acting, open the wrong account, close the browser,
> submit stale automation, and remove passive capture. Success depends on fresh
> state, not on the existence of a click log. The evidence separates real-provider
> runs, automated handoff checks and physical acceptance.”

> “The deliberate limits are local process-owned sessions, bounded web controls,
> no production authentication and no universal screenshot redaction. Physical
> human clicks are outside gateway policy. Voice, Teach and screen sharing are
> not implemented. The next step is repeated independent qualification and
> proving safe reuse of one capability across tenant bindings.”

End on the README's test guide link so reviewers can reproduce the same steps.
