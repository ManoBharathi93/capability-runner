# Supported browser scope

Discovery can learn a workflow without a prepared target profile, **within the
browser limits below**. It does not promise to operate every website.
See [recorded checks](../progress.md) and the [product guide](test-product.md).

## Supported and unsupported controls

| Supported | Not supported |
| --- | --- |
| Visible text/search inputs, ordinary buttons and links | CAPTCHA, canvas-only or inaccessible custom controls |
| Result labels, tables and definition lists | File upload/download, media and select primitives in generic automation |
| Main page and up to three named same-origin frames | Cross-origin frame internals |
| Bounded read-only navigation and the known demo search POST | Arbitrary writes, account creation and open-ended browsing |

The adapter collects at most 64 elements, eight headings and four frames. Nearby
and structural context each stop at 200 characters. Normalized text has an 8,192
character budget; the complete snapshot stays below 65,536 UTF-8 bytes. Model
context has a separate 16,000-character cap. Truncation is explicit and deterministic.
Discovery allows 12 turns, eight action attempts and 300 seconds. Two successive
unchanged fingerprints stop it, alongside the existing repeated-action guard.

ARIA names/roles and native HTML semantics take precedence over bounded DOM
context. Source tags identify actual contributors. There is no full accessibility
tree dump, raw HTML prompt or vision runtime. Credential input values, hidden
content and scripts/styles are excluded. This does not cover arbitrary PII.

## How a new control becomes a saved binding

1. The adapter observes visible controls and issues temporary references.
2. The model proposes a typed inspect, fill, click, complete or failure decision.
3. The gateway checks the reference, ownership and policy before execution.
4. The compiler turns verified properties into a durable application binding.

Each observation advances a session-local generation. A ref such as `12:e4`
belongs to that generation and observation UUID. Old generations fail with
`STALE_ELEMENT_REF` before locator lookup; invented current/future refs fail with
`UNKNOWN_ELEMENT_REF`. Local `e4` may repeat under a new generation without reuse.
References expire on new observations, navigation or observed DOM/control changes.
Dispatch also checks that the uniquely resolved node in its frame is the original node.
Duplicate matches fail; there is no “just click the first one” fallback.

After an action, the adapter awaits document load and two DOM-quiet animation
frames within its configured timeout. It does not prove that all asynchronous
business work has settled. Fresh refs, bounded delta counts and fingerprints
describe the next view. IDs and recognizable clocks/UUIDs do not count as progress.
See [acceptance and size measurements](../../evidence/surface-observation/README.md).

The model cannot send CSS, XPath, JavaScript, shell commands or Playwright code.
Input values use references to the goal. Numeric IDs and recognizable credential
tokens are masked in the new-app presentation; that is not universal PII redaction.

## What authorizes an application

Built-in demo origins are configured. An administrator may add sandbox entry URLs
through the JSON array `CAPABILITY_RUNNER_READ_ONLY_URLS`.

This asserts that GET routes in that scope are safe to read; HTTP GET alone does
not prove the absence of side effects. Other POSTs, cross-origin requests,
credentials in URLs, path escapes and destructive controls are blocked.
Page text, the goal and the model cannot extend the allowlist.

## What counts as completion

The current page must show matching input identity and the requested account
context, with unique visible output fields that the evaluator can parse.
A filled search box or a model saying “done” is insufficient.

Some natural-language meanings and field layouts cannot be verified. Those runs
must return non-success. A generated package stores the capability, profile and
integrity metadata, not invocation values or temporary references.

Replay checks application identity and uses the saved bindings without a model.
Missing targets, ambiguity, wrong identity and drift fail safely. An unobserved
business outcome is not invented; trusted CoreBank MEMBER_NOT_FOUND behavior
comes from its declared contract.

## Preview and human control

Preview images come from the managed browser and are transient and cache-disabled.
The product's human takeover uses the actual headed browser; its preview is not
interactive. Physical clicks bypass gateway policy and have bounded passive
capture. The older typed operator path remains a CLI/test seam.

Active sessions are process-local. Desktop, voice, screen sharing and Teach
are not implemented.
