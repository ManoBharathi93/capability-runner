# Synthetic Demo App

This is the local legacy-style banking target used by Capability Runner P1.5a.

Run it locally with:

```bash
uv run python -m demo_app
```

Primary workflow: member search -> search results -> member details -> savings account.

Deterministic scenarios: `normal`, `slow_search`, and `session_expired`.

The fixture data is synthetic and read-only. There is no member/balance business API for Capability Runner to call, and browser automation is intentionally not implemented in P1.5a.
# Synthetic Target Application

The demo application is deferred to P1.5. It will be the target operated by Capability Runner and will expose synthetic member-servicing flows plus controlled exceptional states.

It is not part of the runner. Production modules under `src/capability_runner/` must not import its fixtures, database, or implementation. No `app.py`, templates, static assets, or fixtures exist in P1.0.