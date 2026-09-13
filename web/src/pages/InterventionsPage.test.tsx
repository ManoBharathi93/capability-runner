import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InterventionsPage } from "./InterventionsPage";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("direct browser handoff", () => {
  it.each(["SUCCESS", "VALIDATION_FAILED"])("renders the backend %s without proxy browser controls", async (outcome) => {
    const initial = { intervention_id: "live", run_id: "run", active: true,
      control_state: "pause_requested", state_label: "Waiting for operator", generation: 1,
      surface_session_id: "same-surface", reason_code: "APPROVAL_REQUIRED" };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      let payload: object = initial;
      if (url.endsWith("/take-control")) payload = { ...initial, control_state: "operator_controlled",
        generation: 2, state_label: "Operator in control" };
      if (url.endsWith("/return-control")) payload = { status: outcome, reason_code: outcome,
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
      expect(message).not.toHaveTextContent("Fresh browser validation passed");
      expect(screen.queryByText("98765", { exact: true })).not.toBeInTheDocument();
    }
    expect(screen.queryByRole("button", { name: "Focus live browser" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([url]) => !String(url).endsWith("/actions"))).toBe(true);
  });
});
