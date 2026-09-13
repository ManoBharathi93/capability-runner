# Synthetic sign-in handoff

**ACCEPTED BASELINE:** the owner requested a login example using the existing
human-control mechanism. This adds a local demo sign-in gate, not production
authentication or new banking operations.

The demo prepends an approval-required Sign in step to the saved savings fixture.
Automation never fills or submits credentials. The human signs in in the retained
browser; a fresh authenticated-state condition permits Replay to continue the
existing lookup. No new Replay checkpoint or recovery contract is needed.

The alternative was general session-expiry recovery, which needs broader recovery
semantics. This example is explicitly sign-in-required, not a claim of universal
expired-session recovery. The existing Savings approval example remains available.

The target uses public synthetic credentials and a process-specific cookie signing
key. Input bodies are bounded; failed login never echoes the password. The product
does not serve browser screenshots for this credential-entry scenario. Native
capture remains bounded and excludes password values; no model is involved.

Checks required before calling this **VERIFIED BEHAVIOR**: same Page/context,
zero credential gateway actions and model calls, authenticated state before resume,
four lookup actions exactly once, fixed 98765/USD, wrong/no login rejection,
closed-browser failure, cookie-free bypass rejection and evidence value omission.
Physical human acceptance remains a separate check.

**VERIFIED BEHAVIOR:** the focused 38-test regression, 12 frontend tests and
headed sign-in check passed. The initial missing workspace marker was corrected.
[Progress](../progress.md) records commands and limits; [evidence](../../evidence/login-handoff/README.md)
contains the actual run. This does not establish physical acceptance.
