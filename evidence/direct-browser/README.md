# Direct-browser handoff evidence

`summary.json` and `evidence.jsonl` are unmodified outputs from run
`intervention-c998ee9d366841039d4a419096e2f8cb`. `ui-check.json` is the unmodified
verification-script result. Captured on 2026-09-13 with:

```powershell
uv run python scripts/verify_workspace_handoff.py --headed
```

The script starts an isolated product, transfers ownership, then uses the original
Playwright Page directly as a stand-in for physical human input. Neither product
semantic action endpoints nor OperatorActionGateway operate the human action.
This is automated evidence; **physical human acceptance remains required**.

The session, BrowserContext and Page identities match before and after return.
The initial automatic actions total three; automatic Savings and operator-gateway
action counts are zero. Fresh validation produces 98765/USD, generation 0 to 3,
zero model calls and no repeated automation effect. Passive click/navigation events
are recorded as observations with human provenance, never EXECUTED gateway results.

Screenshots live in [the testing guide](../../docs/submission/test-product.md).
They show synthetic fixture data only. Negative cases and capture privacy are
covered by [the direct-browser tests](../../tests/end_to_end/test_direct_browser_handoff.py);
those separate assertions should not be inferred from this happy-path JSONL alone.
