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

The adapter collects at most 64 elements and eight headings. The model's view is
bounded to 16,000 characters. Discovery allows 12 turns, eight action attempts and
300 seconds, with a repeated-action stop.

## How a new control becomes a saved binding

1. The adapter observes visible controls and issues temporary references.
2. The model proposes a typed inspect, fill, click, complete or failure decision.
3. The gateway checks the reference, ownership and policy before execution.
4. The compiler turns verified properties into a durable application binding.

References expire on new observations, navigation or observed DOM changes.
Dispatch also checks that the uniquely resolved node is the original node.
Duplicate matches fail; there is no “just click the first one” fallback.

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
