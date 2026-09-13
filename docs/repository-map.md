# Where the code lives

Start with [system flow](submission/system-design.md) if you want the request
path. This page helps you find the implementation.

## Core Python package

All core code lives under `src/capability_runner/`.

| Folder or file | What to read it for | Must stay separate |
| --- | --- | --- |
| `contracts/` | Typed requests, actions, artifacts, observations and results. | No browser, filesystem or model execution. |
| `application/` | Run lifecycle and continuation coordination. | Does not choose individual model actions. |
| `discovery/` | Bounded observe/decide/act loops. | No direct Playwright or unvalidated publication. |
| `discovery/providers/` | Provider HTTP requests and error mapping. | Vendor formats do not enter Replay. |
| `capabilities/` | Build, validate, compile bindings and store packages. | No executable model-generated scripts. |
| `replay/` | Saved-step interpreter and deterministic state checks. | No model or provider dependency. |
| `interaction/` | Action Gateway, Policy Guard and Session Controller. | No invented workflow decisions. |
| `surfaces/` | Browser handles, observations, target resolution and actions. | No banking or model decisions. |
| `intervention/` | Requests for help and the controlled operator test path. | Session Controller remains ownership authority. |
| `evidence/` | Redaction and structured event recording. | Does not scrape engine internals to decide outcomes. |
| `interfaces/` | Transport and operator-console support. | No duplicate execution engine. |
| `bootstrap.py` | Connect concrete implementations. | Engines use injected boundaries. |

## Product and verification

| Location | Purpose |
| --- | --- |
| `demo_app/product_http.py` | Local product API and native browser handoff composition. |
| `demo_app/discovery_workspace.py` | Product Discovery, generated packages and Replay. |
| `demo_app/reviewer_runtime.py` | Reproducible synthetic-bank demo composition. |
| `web/src/` | React pages; renders backend-owned state. |
| `tests/unit/` | Contract and component checks. |
| `tests/integration/` | Browser, package, gateway and engine boundaries. |
| `tests/end_to_end/` | Same-session handoff and continuation. |
| `tests/live/` | Explicitly enabled real-provider checks. |
| `evals/` | Expected banking outcomes and evaluation commands. |
| `evidence/` | Curated run outputs for reviewers. |
| `var/` | Ignored runtime data and personal working checks. |

Production runner modules must not import demo fixtures. The local demo runtime
composes the core for reviewers; it does not make those fixtures production logic.

## The rules that matter

Replay cannot call the model. Automated actions must use Action Gateway.
Playwright handles stay in the browser adapter. Physical human input is the
owner-approved exception: it occurs in the same browser outside gateway policy,
with passive observations and fresh state validation on return.

The frontend cannot decide policy or manufacture success. Evidence records
outcomes supplied through typed events; it does not infer success afterward.

These are **ACCEPTED BASELINE** boundaries. Static import checks protect part
of them. Runtime evidence is required before calling behavior **VERIFIED BEHAVIOR**.
See [progress](progress.md) for completed checks.
