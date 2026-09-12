# Submission Readiness Report

## Executive verdict

**READY WITH GAPS**.

The local package now has a test-backed discovery, capability, replay, safety, and same-session
handoff core; stable reviewer commands; an evaluator-facing root README; the required seven-section
`REPORT.md`; and curated genuine runtime evidence. Public repository publication is still external
and unverified. The refreshed provider-backed through-line now directly evidences bounded
Discovery decisions, capability production, and complete fresh Replay lifecycle without raw model
content or sensitive invocation values.

## What is ready

- Genuine provider-backed discovery against the synthetic live UI was previously executed and is
  recorded in `docs/progress.md`.
- Discovery compiles into a validated, versioned `CapabilityDefinition`; fresh replay succeeds for
  different inputs without a model and returns typed outputs/business outcomes.
- Action Gateway, Policy Guard, Session Controller, and trusted semantic bindings form one enforced
  action path for discovery and replay.
- Real Chromium tests cover successful replay, not-found, permission restriction, session expiry,
  bounded slowness, same-session operator handoff, and safe approval continuation.
- `capability-runner demo` now exposes verified through-line, intervention, and exception commands.
- Terminal demo failures persist bounded sanitized surface-state evidence; known business outcomes
  remain distinctly classified.
- Fresh model-free evidence records Replay lifecycle plus sanitized intervention context through
  approval, operator action, fresh-state validation, and same-session resume.
- Fresh provider-backed evidence records real Discovery start, bounded semantic decisions and
  authorized actions, completion, capability build/validate/store/load, and fresh Replay success.
- The root README documents fresh setup, Chromium installation, provider configuration, exact live
  and model-free commands, expected outputs, checks, and limitations.
- `REPORT.md` has exactly the seven assignment headings, and `/evidence/` contains a generated
  capability plus genuine Discovery/Replay, exceptional-outcome, and terminal-failure records.
- The latest completed ordinary gates are 335 passed with 6 live cases deselected, Ruff clean,
  Pyright clean, and 31 locked packages unchanged.
- The current `.env.example` declares all provider-selection, model, key, and Gemma endpoint names
  expected by `docs/providers.md`, using empty/placeholder values.

## Remaining findings

| Priority | Gap | Current evidence | Required closure |
| --- | --- | --- | --- |
| B-08 | Public repository delivery is unverified | Workspace has no Git metadata or public URL | Owner must initialize/review/push the intended files and verify anonymous public access. |

## Findings resolved by P5.2

| Priority | Resolved finding | Verification |
| --- | --- | --- |
| B-02 | Reproducible product demo entry point | `capability-runner demo through-line`, `intervention`, and `exception` execute the public application composition; five focused command tests passed. |
| B-06 | Rich failure evidence was not connected | Terminal Discovery/Replay failures call bounded Browser Surface Adapter capture. Existing `session_expired` Replay persisted a sanitized surface-state error event. |

## Findings resolved by P5.3

| Priority | Resolved finding | Verification |
| --- | --- | --- |
| B-01 | Evaluator README | Fresh setup, Chromium, provider selection, exact commands, expected results, offline checks, evidence, and limits are documented; local links pass. |
| B-03 | Required design report | `REPORT.md` exists and an exact-heading check found all seven required headings in order with no additional second-level headings. |
| B-04 | Curated submission evidence | Six selected files were hash-equal to genuine runtime sources; all JSON/JSONL parses and summary-relative artifact/evidence paths resolve. |

## Findings resolved by P5.4a

| Priority | Resolved finding | Verification |
| --- | --- | --- |
| B-07 | Intervention context was split across private runtime state | Fresh curated JSONL carries a sanitized capability/version, blocked step/index and target, current state, stop reason, and input names alongside same-session handoff/resume events; runtime values remain private. |

## Findings resolved by P5.4a.1

| Priority | Resolved finding | Verification |
| --- | --- | --- |
| B-05 | Curated evidence lacked the new Discovery decision metadata | A genuine Gemma/Chromium reviewer command succeeded in five model calls; its byte-identical curated JSONL contains bounded Discovery decisions and fingerprints through capability production and complete fresh Replay, with zero prohibited privacy matches. |

## Reviewer friction and overclaims

The root README and report now present the top-level story as Discover, Compile, Replay, Intervene,
and Resume safely. Internal phase records remain supporting evidence rather than the primary
reviewer navigation.

Claims that must not appear in submission materials:

- that Playwright installs Chromium automatically;
- that the hand-authored fixture is a generated capability;
- that pytest temporary files or documented assertions are `/evidence/` artifacts;
- that screenshots are persisted failure evidence;
- that Discovery or Replay currently emits complete lifecycle/rationale evidence;
- that operator identity is explicitly stored in every action event;
- that tenant isolation, production authentication, crash recovery, distributed enforcement,
  SOC 2 controls, or desktop portability are implemented;
- that a public repository exists until its URL and contents are verified.

The optional React frontend, capability catalog, generated code, second adapter, and multi-tenant
runtime would add reviewer-facing complexity without closing the current mandatory blockers.

## Reproducibility inventory

| Need | Current state |
| --- | --- |
| Python/dependency setup | `uv sync --all-groups` exists and lock is current. |
| Browser setup | `uv run playwright install chromium` is documented in the root README. |
| Offline ordinary checks | `uv run pytest`, `uv run ruff check .`, `uv run pyright`, and `uv lock --check`; ordinary pytest excludes external-provider live cases. |
| Synthetic target | `uv run python -m demo_app` starts loopback Flask on port 5000, but this is not the capability demo. |
| Live provider configuration | `.env.example` has the expected names; README explains explicit provider selection and `.env`/process loading. |
| Genuine discovery/build/replay | `capability-runner demo through-line`; live public-entrypoint acceptance passed. |
| Human intervention/resume | `capability-runner demo intervention`; same-session HTTP operator/resume acceptance passed. |
| Generated submission artifact | Present at `evidence/through-line/capabilities/lookup_savings_balance/1.0.0.json`. |
| Discovery/replay submission logs | Present at `evidence/through-line/evidence.jsonl` with a correlated run summary. |
| Exceptional runtime run | Model-free business-outcome summary and JSONL are curated under `evidence/exception/`; terminal failure evidence is under `evidence/failure/`. |

## Authorized follow-up boundaries

### P5.2: Reproducibility and demo entry point only

Completed with the smallest stable command surface needed to run:

1. genuine discovery from a goal and configured provider;
2. builder/validator/store publication of the generated artifact;
3. fresh model-free replay with supplied inputs;
4. one approval/intervention/resume scenario;
5. one exceptional replay with structured and richer failure evidence.

The implementation reuses the existing engines, gateways, session controller, operator page,
contracts, and stores. It did not add a React UI, provider, second workflow engine, general
recovery, tenant platform, or optional teaching work.

### P5.3: Documentation, evidence, and submission packaging only

Completed locally. The root README, exact-heading `REPORT.md`, and curated evidence package are
present. File existence, JSON parsing, relative paths, local documentation links, high-confidence
secret signatures, credential-template values, private addresses, and workstation paths were
checked. No Git metadata or public URL exists, so committed contents and anonymous repository
access remain **EXTERNAL-MANUAL**.

P5.3 must not change runtime behavior except to correct a command or packaging defect found while
reproducing the already-authorized P5.2 path.

### P5.4: Optional polish only

Separately scope any short recording, React product frontend, capability catalog, stability report,
second adapter, tenant-variant demonstration, or visual refinement. P5.4 is not required to close
the current assignment blockers and must not delay submission readiness.

## P5.1 audit evidence

P5.1 changed documentation only. It did not rerun live provider calls or the full browser suite.
The audit performed these fresh checks:

- pytest collection: 334 total cases, comprising 329 ordinary and 5 live cases;
- environment template: all eight documented provider variable names present, with empty or
  placeholder values;
- intended-public text scan after one hygiene correction: no Windows user paths, non-loopback
  private IPv4 URLs, credential assignments, or bearer-token patterns;
- file inventory: no root `REPORT.md`, no generated artifact/logs under `/evidence/`, no product
  CLI/module entry point, and no React implementation;
- evidence call-site inspection: gateway and intervention events only;
- failure-evidence inspection at P5.1: bounded textual capture existed but had no production caller.

The P4.3 full-gate results remain the current runtime verification baseline because P5.1 changed no
source, tests, package configuration, or lock data.

## P5.2 readiness update

P5.2 resolves the product demo entry-point and connected richer-failure-evidence findings. The
mandatory matrix is now 24 PASS, 3 PARTIAL, and 3 MISSING. The executive verdict remains **NOT
READY** until P5.3 updates the root README, creates `REPORT.md`, curates genuine sanitized output
under `/evidence/`, and verifies public repository delivery. E-01 and H-02 remain partial because
the demo does not add complete Discovery reasoning/lifecycle events or widen the public
intervention contract.

## P5.3 readiness update

P5.3 closes L-01, L-02, and L-03. The mandatory matrix is now 27 PASS, 2 PARTIAL, and 1 MISSING.
The local verdict is **READY WITH GAPS**: E-01 and H-02 are transparent implementation limits, and
L-04 is the unperformed public-repository delivery step. P5.3 changed documentation and copied
runtime artifacts only, so the P5.2 full runtime gates remain the current baseline.

Fresh P5.3 checks on 2026-09-12 passed for exact report headings, 28-file local Markdown links,
required file existence, JSON/JSONL parsing, runtime-relative evidence paths, six source-to-curated
hash comparisons, 156-file portability/private-address/bearer scanning, high-confidence secret
signatures, and credential-bearing `.env.example` values. The public CLI help, fresh model-free
exception command, and model-free intervention command were also exercised; their generated
summaries reached the expected results.

## P5.4a evidence-observability update

The narrowly authorized P5.4a work adds passive sanitized lifecycle evidence without changing
Discovery decisions, model-free Replay behavior, policy, session ownership, or continuation
semantics. Fresh curated exception and intervention runs now prove complete Replay lifecycle and a
capability/step/current-state intervention context bundle. H-02 therefore moves to PASS, producing
28 PASS, 1 PARTIAL, and 1 MISSING.

E-01 remains PARTIAL. Discovery now emits bounded lifecycle and decision-classification metadata,
and focused tests verify chronology and privacy, but the existing genuine provider-backed
through-line predates those events. No provider was configured for a fresh genuine Discovery run,
so the curated package does not claim evidence it cannot reproduce. L-04 remains the external
public-repository delivery step.

## P5.4a.1 readiness update

The existing neutral live ModelClient smoke passed against Gemma, and the public
`capability-runner demo through-line` command completed a genuine Discovery-to-Compile-to-fresh-
Replay run. The three refreshed curated files are byte-identical to their runtime sources, parse
cleanly, and contain zero prohibited endpoint, credential, token, developer-path, sensitive-value,
raw-model-content, raw-goal/input-map, HTML, or selector matches. E-01 therefore moves to PASS.

The mandatory matrix is now 29 PASS, 0 PARTIAL, and 1 MISSING. L-04 public repository delivery is
the sole remaining gap and remains external/manual.
