# Supported browser scope

The owner-authorized claim is: Profile-less Discovery supports previously unseen web applications
within the current Browser Surface capabilities. Implementation and completed acceptance evidence
are tracked separately in [progress](../progress.md); a scripted test is not live-model acceptance.

The supported primitives are visible HTML text/search inputs, ordinary form submission, links,
buttons, labelled result fields, tables, definition lists, and deterministic navigation. Standard
roles, accessible names and label associations are preferred. The main document and at most three
named same-origin frames are observed. CAPTCHA, canvas-only controls, inaccessible custom widgets,
native desktop applications, cross-origin frame internals, select/file/download/media primitives,
and open-ended exploration are unsupported.

There are two authoring paths. A known application uses its trusted ApplicationProfile and optional
required completion targets. A new application starts with zero target bindings. BrowserSurfaceAdapter
collects at most 64 visible elements, eight headings, short labels and nearby snippets. The model
receives a presentation bounded to 16,000 characters, never a DOM dump. Input values are represented
by goal-span references. Numeric identifiers and recognizable credential tokens are masked in the
new-app presentation. This is a synthetic-sandbox feature, not universal PII or screenshot redaction.

The model proposes strictly typed inspect, fill, click, complete, or unsupported/fail decisions.
It cannot supply CSS, XPath, JavaScript, shell commands, Playwright code, or a confidence score.
An element reference belongs to one observation. A new observation, navigation, or observed DOM
mutation invalidates it; dispatch also checks that the uniquely resolved node is the original node.
The same ActionGateway and SessionController enforce policy, ownership and generation.

Application URLs require operator configuration. Built-in demo origins are allowed; additional
read-only sandbox entry URLs can be listed in `CAPABILITY_RUNNER_READ_ONLY_URLS` as a JSON array.
This is an administrator assertion that GET routes in that path scope are read-only. Unknown effects
are denied. The existing CoreBank search POST is separately allowed by its exact route in demo
composition. Other POST requests, cross-origin requests, credentials in URLs, path escapes and
destructive controls are blocked. Page instructions, model output and user goals cannot change this
configuration. Do not add a real application merely because its URL is reachable.

Completion must cite current, visible, uniquely resolved result fields. Every supplied input must
have matching displayed identity evidence; a populated search box is insufficient. Selected table
category context must agree with the goal and the result page. The deterministic evaluator must
extract every declared output successfully. Arbitrary English is accepted as input; some meanings,
field structures and unnamed inputs cannot be verified by this bounded read-only extraction path
and must return non-success. This does not prove arbitrary natural-language entailment.

The deterministic compiler derives semantic names and browser bindings from observed properties.
Bindings prefer exact role/name and label resolution, with verified structural paths when necessary.
Duplicate matches fail; the model cannot nominate a first match. Required bindings carry observation
fingerprints and actual uniqueness/re-resolution evidence. A logical package stores a selector-free
typed capability, an application profile, and integrity metadata as separate JSON files. Input
instances and temporary element references do not become durable selectors or workflow literals.

Replay loads the package, checks origin/entry-path/title identity before actions, and uses the
existing ReplayEngine and non-LLM StateEvaluator. Its construction imports no ModelClient and has no
LLM fallback. Binding drift, ambiguity, wrong identity and application mismatch cause structured
failure. Generated packages do not invent business outcomes from a successful trace; trusted-profile
outcomes such as MEMBER_NOT_FOUND remain supported.

The product preview is an ephemeral PNG from the same managed browser. It is read-only, bounded and
cache-disabled. Only the current frame is retained by the client. Operator actions continue through
the existing typed intervention controls. Active run/session state is process-local. Discovery is
bounded to 12 turns, eight action attempts and 300 seconds, with a repeated-action stop. Teach,
voice and screenshare remain outside this milestone.
