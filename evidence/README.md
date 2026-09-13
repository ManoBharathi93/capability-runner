# Evidence: what to inspect

These are reviewed copies of actual run outputs using synthetic data.
The recorded JSON and logs were copied unchanged; they were not rewritten to
make a run look successful.

| Question | Open | What it shows |
| --- | --- | --- |
| Did a real model complete Discovery? | [Through-line summary](through-line/summary.json) | Five Discovery calls, saved artifact, fresh Replay with zero Builder/Replay calls. |
| What was saved? | [Capability JSON](through-line/capabilities/lookup_savings_balance/1.0.0.json) | Typed input/output, four semantic actions, conditions and MEMBER_NOT_FOUND. |
| Where are both run logs? | [Through-line events](through-line/evidence.jsonl) | Discovery, build/store/load and fresh Replay in one correlated log. |
| Does a missing member stay distinct from failure? | [Not-found summary](exception/summary.json) and [events](exception/evidence.jsonl) | BUSINESS_OUTCOME / MEMBER_NOT_FOUND, no model. |
| What happens on a technical failure? | [Failure events](failure/evidence.jsonl) | TARGET_NOT_FOUND with bounded visible text from an expired session. |
| Does Checking work on another app? | [Checking summary](checking/ui-summary.json) | Real-model Discovery, then different-input Replay: 15840/USD, zero Replay calls. |
| Does the native handoff retain the browser? | [Direct-browser summary](direct-browser/summary.json) | Same Page/context/session, ownership changes, validated continuation. Automated input, not physical acceptance. |

## Reading the records

Start with a summary, then inspect the matching event log. A shared run ID ties
events together. Discovery and fresh Replay have different session IDs.
Handoff, by contrast, must retain its original browser identity.

The Checking run also includes its [capability](checking/capability.json),
[Discovery log](checking/discovery.jsonl) and [Replay log](checking/replay.jsonl).
Its generated binding remains in the local package. A second package proves a
second app, not reuse of one identical artifact across tenants.

The older [intervention summary](intervention/summary.json) and
[event log](intervention/evidence.jsonl) use controlled HTTP operator actions.
Use [direct-browser evidence](direct-browser/README.md) for current product semantics.

## Privacy and proof limits

Artifacts store parameter references. Logs omit fill values, credentials and raw
provider payloads. Synthetic balances remain where they prove output extraction.
Failure evidence is bounded safe text, not a full DOM archive.

The [screenshot guide](../docs/submission/test-product.md) contains reviewed synthetic
screens. Screenshots and automated Page input do not establish physical human
acceptance. Local runtime files under `var/` are ignored working data; they are
not automatically submission evidence.
