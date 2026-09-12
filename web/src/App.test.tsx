import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const capability = {
  capability_id: "lookup_savings_balance",
  version: "1.0.0",
  name: "Lookup savings balance",
  description: "Find a member savings account and return its balance.",
  application: "corebank",
  surface_kind: "browser",
  status: "READY",
  input_count: 1,
  output_count: 2,
  step_count: 1,
  updated_at: "2026-01-01T00:00:00Z",
  definition: {
    inputs: [{ name: "member_id", value_type: "STRING", required: true, sensitive: true }],
    outputs: [{ name: "currency", value_type: "CURRENCY_CODE", source: { kind: "target_text", parser: "currency_code", target: { value: "member.account.balance" } } }],
    steps: [{ kind: "action", step_id: "open_savings", action: { kind: "click", target: { value: "member.accounts.savings" } }, precondition: null, postcondition: null, retry_policy: null }],
    success_conditions: [{}],
    business_outcomes: [{ code: "MEMBER_NOT_FOUND", description: "The member was not found." }],
  },
};

const run = {
  run_id: "run-safe",
  demo_kind: "replay",
  status: "BUSINESS_OUTCOME",
  capability_id: "lookup_savings_balance",
  capability_version: "1.0.0",
  replay_result: "BUSINESS_OUTCOME",
  business_outcome: "MEMBER_NOT_FOUND",
  replay_model_calls: 0,
  browser_action_count: 2,
  event_count: 1,
  created_at: "2026-01-01T00:00:00Z",
};

function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Capability Runner product frontend", () => {
  it("renders backend-owned home metrics and navigates", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => String(input).includes("/api/capabilities")
      ? json({ capabilities: [capability] })
      : json({ capability_count: 1, run_count: 1, active_run_count: 0, intervention_count: 0, verified_run_count: 1, system_health: "UNAVAILABLE", environment: "LOCAL_REVIEW", recent_runs: [run] })));
    renderAt("/");

    expect(await screen.findByText("Verified Runs")).toBeInTheDocument();
    expect(screen.getByText("1 total records")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Capabilities" })).toHaveAttribute("href", "/capabilities");
  });

  it("renders validated capability schemas and steps", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json({ capabilities: [capability] })));
    renderAt("/capabilities/lookup_savings_balance");

    expect(await screen.findByText("Capabilities Library")).toBeInTheDocument();
    expect(screen.getAllByText("Lookup savings balance").length).toBeGreaterThan(1);
    expect(screen.getByText("string (sensitive)", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Open Savings")).toBeInTheDocument();
  });

  it("renders a business outcome and sanitized lifecycle", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/events")) return json({ events: [{ event_id: "event-1", timestamp: "2026-01-01T00:00:00Z", event_type: "lifecycle", component: "replay-engine", run_id: "run-safe", session_id: null, step_id: "open_savings", action_id: null, outcome: "completed", reason_code: "REPLAY_STEP_COMPLETED", summary: null, metadata: {} }] });
      return json(run);
    }));
    renderAt("/runs/run-safe");

    expect(await screen.findByText("Member Not Found")).toBeInTheDocument();
    expect(screen.getAllByText("Replay Step Completed").length).toBeGreaterThan(0);
    expect(screen.getByText("Replay model calls")).toBeInTheDocument();
  });

  it("keeps replay input masked and does not render its value", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "POST") return json({ run }, 201);
      return json({ runs: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderAt("/runs");

    const input = await screen.findByLabelText("Member ID");
    expect(input).toHaveAttribute("type", "password");
    await userEvent.type(input, "private-member-id");
    await userEvent.click(screen.getByRole("button", { name: "Start Replay" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/replay", expect.objectContaining({ method: "POST" })));
    expect(screen.queryByText("private-member-id")).not.toBeInTheDocument();
  });

  it("renders historical intervention context without live controls", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json({ intervention_id: "intervention-safe", run_id: "run-safe", capability_id: "lookup_savings_balance", reason_code: "APPROVAL_REQUIRED", summary: "Approval was required.", control_state: "terminal", state_label: "Completed intervention", active: false, blocked_action: "member.accounts.savings", replay_result: "SUCCESS" })));
    renderAt("/interventions/intervention-safe");

    expect(await screen.findByText("Human intervention recorded")).toBeInTheDocument();
    expect(screen.getByText("Live surface closed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Return Control to Agent" })).not.toBeInTheDocument();
  });

  it("shows safe backend errors without leaking response internals", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json({ error: { code: "SAFE_ERROR", summary: "Safe public summary." } }, 503)));
    renderAt("/evidence");

    expect(await screen.findByText("Safe public summary.")).toBeInTheDocument();
    expect(screen.queryByText("SAFE_ERROR")).not.toBeInTheDocument();
  });

  it("accepts arbitrary Discovery text and renders backend lifecycle", async () => {
    const fetchMock = vi.fn(async () => json({ run_id: "run-safe", status: "SUCCESS", capability: null, application: "corebank-known",
      view_available: false, events: [{ event_id: "event-1", event_type: "lifecycle", component: "discovery-engine",
        reason_code: "DISCOVERY_COMPLETED", metadata: {} }] }, 202));
    vi.stubGlobal("fetch", fetchMock);
    renderAt("/discover");
    const button = screen.getByRole("button", { name: "Discover Capability" });
    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Workflow goal"), "Open member 67890 and tell me their balance.");
    expect(button).toBeEnabled();
    await userEvent.click(button);
    expect(await screen.findByText("Discovery Completed")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/discovery", expect.objectContaining({ method: "POST",
      body: JSON.stringify({ goal: "Open member 67890 and tell me their balance.", application: "corebank-known" }) }));
  });
});
