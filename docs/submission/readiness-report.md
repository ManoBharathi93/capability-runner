# Submission readiness report

## Verdict

**The core scope is implemented and supported by evidence; physical handoff acceptance remains outstanding.** This is a conditional assessment of meeting the requirements, not a claim of exceeding them. The earlier unconditional READY verdict overstated the acceptance status.

The assignment asks for one complete workflow touching every core requirement. Savings lookup, account creation and shopping checkout are example goals, not three required implementations. This submission deliberately implements read-only savings and checking outcomes plus approval/handoff. It does not create accounts or operate a shopping site. Extra UI and a second outcome do not compensate for a broken required handoff.

The source is published at [github.com/ManoBharathi93/capability-runner](https://github.com/ManoBharathi93/capability-runner) on `main`. The repository is public, and anonymous access to both the repository page and raw README returned HTTP 200 after publication. The assignment audit is recorded in [requirement-traceability.md](requirement-traceability.md).

## Implemented and verified

The repository contains a complete Discovery-to-Replay vertical slice against real synthetic banking UIs. Discovery accepts natural-language goals, uses a configured model in a bounded observe-decide-act loop, and sends actions through the shared Action Gateway. Successful verified traces compile into typed, versioned capability JSON with a separate application profile. Fresh Replay loads that package, accepts different inputs, checks current state and identity, and returns typed outputs without a Model Client dependency.

The React product provides Discover, Capability Library, Runs, Human Interventions, Evidence, and a clearly disabled Teach route. The Discovery workspace shows the actual managed browser session, a structured timeline, the capability and binding, and a different-input Replay form. A second structurally different application, LegacyBank B, has completed real-provider profile-less Discovery and fresh model-free Replay. This is evidence for bounded generic browser discovery, not universal website support or reuse of one identical capability across tenants.

The current same-session handoff pauses before an approval-required action and transfers ownership of the retained browser to the human. Physical clicks occur in that browser, outside gateway enforcement; bounded passive observations record event metadata. Handback re-observes state, advances the generation and resumes only after validation, without repeating the blocked action. Automated actions still require Action Gateway. The earlier product proxy-button flow is superseded; its CLI test seam remains separate. The local operator UI is unauthenticated and process-local.

Headed Playwright tests retain the same Page and BrowserContext and independently verify the resumed result. They are automated stand-ins, not physical human acceptance. The owner's screenshot shows the old interface. A fresh client loaded the current controls against the same active session without changing ownership. Hard-refresh the product tab, then complete the [five physical handoff steps](test-product.md#5-physically-take-over-the-existing-browser). The current labels are **Managed browser preview** and **Return control to automation**. Returning control without opening Savings must fail validation; the system must not invent success to make a demo appear complete.

The reported session subsequently reached human ownership but returned VIEW_UNAVAILABLE for its preview. Its live browser usability remains unresolved. A refreshed interface alone is not a successful handoff; the physical check must complete against a usable managed browser.

Curated evidence under `evidence/` includes a real provider-backed Discovery and fresh Replay through-line, a generated capability, a model-free business outcome, an intervention run, and bounded terminal failure state. The records omit raw prompts, model payloads, selectors, raw DOM, credentials, private endpoints, and invocation values.

The latest recorded verification is:

- 380 ordinary Python tests passed; 8 opt-in live tests were deselected by default;
- 11 frontend tests passed;
- TypeScript typecheck and the Vite production build passed;
- Ruff and Pyright passed;
- the Python lock consistency check passed;
- the deterministic banking evaluation passed 13 of 13 cases with nine matching fresh Replay results, three generated profiles, zero false successes, zero wrong-entity successes, zero unsafe actions, and zero Replay model calls.

The exact commands and dated evidence are in [progress.md](../progress.md). Real-provider successes and failures are recorded separately; no reliability percentage is inferred from a small number of attempts.

The package checks cover independent savings/checking values, stored Replay without provider configuration, and wrong-account completion rejection in both directions. Direct-browser tests cover successful continuation, unchanged state, wrong account, browser closure, missing passive capture and capture privacy. See [curated native handoff evidence](../../evidence/direct-browser/README.md), [savings run record](screenshots/savings-ui-check.json), and [checking evidence](../../evidence/checking/ui-summary.json). No physical acceptance is inferred from these automated checks.

## Reviewer entry points

Start with the [screenshot testing guide](test-product.md). Use the root [README](../../README.md) for setup and the shortest reproducible commands. Use [manual-test-guide.md](manual-test-guide.md) for additional product inputs, expected outputs, negative cases, CLI checks, the 13-case evaluation, and focused browser safety tests. The root [REPORT](../../REPORT.md) explains the architectural decisions and trade-offs in the seven headings required by the assignment.

## Remaining limitations

The implemented browser scope is allowlisted and read-only. It supports visible ordinary HTML controls, bounded same-origin frames, and current input/output extraction; unsupported or ambiguous controls fail closed. Sessions and intervention ownership live in one process. Provider availability and decision quality can affect Discovery, while Replay remains provider-independent. Generated packages prove observed interactions and declared outcomes, not unobserved business outcomes.

The product does not include production authentication, durable browser-session recovery, distributed scheduling, encrypted artifact storage, universal screenshot or semantic PII redaction, a desktop adapter, or automated profile repair. Voice, screen sharing, and Teach are not implemented. The evaluation harness is regression evidence rather than a persisted draft-to-approved qualification workflow. Reuse of one byte-identical capability across two tenant profiles has not yet been demonstrated.

Native human capture is bounded and best effort, not a tamper-proof audit trail. A human must stop interacting after returning control. The next priority is physical handoff acceptance and clear reviewer operation, followed by stronger data handling and an explicit cross-tenant reuse experiment. These limits are documented cuts in a synthetic-data review build, not evidence of production banking readiness. Adding unrelated business workflows would not resolve them.
