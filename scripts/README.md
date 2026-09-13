# Developer scripts

- `verify_discovery_workspace.py --application corebank-known`: real-provider savings
  Discovery, different-input Replay and member-not-found through the product UI.
- `verify_discovery_workspace.py --application bank-b --product checking`: checking
  Discovery and different-input Replay. Run Discovery scripts one at a time against
  the running product. They write local run summaries and screenshots.
- `verify_workspace_handoff.py --headed`: starts an isolated product, retains the
  managed Page, and supplies automated direct-browser input as a stand-in for the
  physical human. It checks identity, ownership, continuation and responsive routes.
  No model or existing product server is needed. This script's direct Page access is
  a test seam, not a browser-driving API exposed by the product.
- `capture_ui.py`: the older general UI capture utility.

Build the client first. See the [visual reviewer guide](../docs/submission/test-product.md)
for physical testing and [progress](../docs/progress.md) for recorded verification.
