import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InterventionsPage } from "./InterventionsPage";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("direct browser handoff", () => {
  it.each([true, false])("checks the sign-in scenario returned by the backend (matching=%s)", async (matching) => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const payload = init?.method === "POST" ? {
        intervention_id: "returned", blocked_action: matching ? "session.sign_in" : "member.accounts.savings",
      } : { interventions: [] };
      return new Response(JSON.stringify(payload), { headers: { "Content-Type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<MemoryRouter initialEntries={["/interventions"]}><Routes>
      <Route path="/interventions" element={<InterventionsPage />} />
      <Route path="/interventions/:interventionId" element={<p>Requested handoff opened</p>} />
    </Routes></MemoryRouter>);
    await userEvent.click(await screen.findByRole("button", { name: "Start Sign-in Handoff" }));
    if (matching) {
      expect(await screen.findByText("Requested handoff opened")).toBeInTheDocument();
    } else {
      expect(await screen.findByText(/running backend returned a different handoff/)).toBeInTheDocument();
      expect(screen.queryByText("Requested handoff opened")).not.toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Open returned handoff" })).toHaveAttribute("href", "/interventions/returned");
    }
    const posts = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(posts).toHaveLength(1); // Do not automatically stop an existing human session.
    expect(posts[0][1]?.body).toBe(JSON.stringify({ handoff_kind: "sign_in" }));
  });

  it("keeps sign-in credentials out of the product preview", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      intervention_id: "login", run_id: "run", active: true,
      handoff_kind: "sign_in", control_state: "pause_requested", generation: 1,
      state_label: "Waiting for operator", reason_code: "APPROVAL_REQUIRED",
    }), { headers: { "Content-Type": "application/json" } })));
    render(<MemoryRouter initialEntries={["/interventions/login"]}><Routes>
      <Route path="/interventions/:interventionId" element={<InterventionsPage />} />
    </Routes></MemoryRouter>);
    await screen.findByRole("heading", { name: "Sign in in the managed browser" });
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Demo password")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Return control to automation" })).toBeDisabled();
  });

  it.each(["SUCCESS", "VALIDATION_FAILED"])("renders the backend %s without proxy browser controls", async (outcome) => {
    const initial = { intervention_id: "live", run_id: "run", active: true,
      control_state: "pause_requested", state_label: "Waiting for operator", generation: 1,
      surface_session_id: "same-surface", reason_code: "APPROVAL_REQUIRED" };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      let payload: object = initial;
      if (url.endsWith("/take-control")) payload = { ...initial, control_state: "operator_controlled",
        generation: 2, state_label: "Operator in control" };
      if (url.endsWith("/return-control")) payload = { status: outcome,
        reason_code: outcome === "SUCCESS" ? outcome : "RESUME_STATE_UNVERIFIED",
        outputs: { balance_minor_units: 98765, currency: "USD" },
        generation_after: outcome === "SUCCESS" ? 3 : null };
      return new Response(JSON.stringify(payload), { headers: { "Content-Type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<MemoryRouter initialEntries={["/interventions/live"]}><Routes>
      <Route path="/interventions/:interventionId" element={<InterventionsPage />} />
    </Routes></MemoryRouter>);
    await screen.findByRole("button", { name: "Take control" });
    expect(screen.getByRole("button", { name: "Return control to automation" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Savings" })).not.toBeInTheDocument();
    expect(screen.getByText("Preview only")).toBeInTheDocument();
    expect(screen.getByText(/Member Details is the starting page/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Take control" }));
    expect(await screen.findByRole("button", { name: "Focus live browser" })).toBeEnabled();
    expect(screen.getByText("Human reviewer")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Return control to automation" }));
    const message = await screen.findByRole("status");
    if (outcome === "SUCCESS") {
      expect(message).toHaveTextContent("Fresh browser validation passed");
      expect(screen.getByText("3", { exact: true })).toBeInTheDocument();
      expect(screen.getByText("98765", { exact: true })).toBeInTheDocument();
    } else {
      expect(message).toHaveTextContent("Resume did not succeed");
      expect(message).toHaveTextContent("The runner then closed the browser");
      expect(message).toHaveTextContent("Member Details alone is not sufficient");
      expect(message).not.toHaveTextContent("Fresh browser validation passed");
      expect(screen.queryByText("98765", { exact: true })).not.toBeInTheDocument();
    }
    expect(screen.queryByRole("button", { name: "Focus live browser" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([url]) => !String(url).endsWith("/actions"))).toBe(true);
  });

  it.each([
    { reason: "RESUME_STATE_UNVERIFIED", kind: "savings_approval", expected: "Member Details alone is not sufficient" },
    { reason: "RESUME_STATE_UNVERIFIED", kind: "sign_in", expected: "wait for the Signed in as demo-reviewer message" },
    { reason: "BROWSER_SESSION_CLOSED", kind: "savings_approval", expected: "managed browser was already closed" },
  ])("explains historical $kind / $reason after reopening", async ({ reason, kind, expected }) => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      intervention_id: "ended", run_id: "run", active: false,
      blocked_action: kind === "sign_in" ? "session.sign_in" : "member.accounts.savings",
      state_label: reason === "BROWSER_SESSION_CLOSED" ? "FAILURE" : "VALIDATION_FAILED",
      reason_code: reason, reason: "Human approval/action is required before automation can continue.",
    }), { headers: { "Content-Type": "application/json" } })));
    render(<MemoryRouter initialEntries={["/interventions/ended"]}><Routes>
      <Route path="/interventions/:interventionId" element={<InterventionsPage />} />
    </Routes></MemoryRouter>);
    const message = await screen.findByRole("status");
    expect(message).toHaveTextContent(expected);
    expect(screen.getByText(/Recorded outcome:/)).toBeInTheDocument();
    expect(screen.queryByText("Human approval/action is required before automation can continue.")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Return control to automation" })).not.toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    if (reason === "BROWSER_SESSION_CLOSED") {
      expect(message).not.toHaveTextContent("The runner then closed the browser");
    }
  });
});
