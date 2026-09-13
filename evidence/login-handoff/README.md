# Synthetic sign-in handoff evidence

[Summary](summary.json), [events](evidence.jsonl), and [UI check](ui-check.json)
come from an isolated headed product run. The summary and log were copied
unchanged from its runtime directory. Input was supplied by Playwright as an
automated stand-in, not by a physical reviewer.

The runner paused before Sign in. The test supplied public synthetic credentials
in the original browser, returned control, and verified the authenticated state.
Replay then performed the four Savings lookup actions exactly once and returned
98765/USD. Page/context/session identity stayed unchanged. Credential gateway
actions, operator gateway actions and model calls were zero.

This is a sign-in-required demo fixture, not a newly discovered login capability,
production authentication or universal expired-session recovery. Credential-entry
preview images are disabled by the product API. Failure tests cover wrong/no
login, closed browser, missing session cookie and evidence omission of entered values.

Reproduce with `uv run python scripts/verify_login_handoff.py` after building the
frontend. The script updates these curated outputs and screenshots; inspect
changes before publishing them. Physical acceptance remains a separate manual check.
