import { ArrowLeft, Check, Hand, Square } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useNavigate, useParams } from "react-router-dom";

import { apiRequest, errorMessage } from "../api";
import { EmptyState, ErrorState, LoadingState, StatusBadge, formatDate, humanize } from "../components";
import { useApi } from "../useApi";
import type { Intervention } from "../types";

export function InterventionsPage() {
  const { interventionId } = useParams();
  return interventionId ? <InterventionDetail key={interventionId} interventionId={interventionId} /> : <InterventionList />;
}

function InterventionList() {
  const interventions = useApi<{ interventions: Intervention[] }>("/api/interventions");
  const navigate = useNavigate();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function start() {
    setStarting(true); setError(null);
    try {
      const result = await apiRequest<Intervention>("/api/interventions", { method: "POST" });
      navigate(`/interventions/${result.intervention_id}`);
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setStarting(false); }
  }
  return <div className="page-stack page-enter">
    <section className="page-title split"><div><p className="eyebrow">SAME-SESSION HANDOFF</p>
      <h2>Human Interventions</h2><p>Take over the managed browser when automation needs your help.</p>
    </div><button className="button button-primary" type="button" onClick={start} disabled={starting}>
      <Hand size={17} />{starting ? "Opening..." : "Start Demo Handoff"}</button></section>
    {error && <p className="inline-error">{error}</p>}
    <section className="panel"><div className="panel-heading"><h3>Intervention History</h3></div>
      {interventions.loading ? <LoadingState /> : interventions.error ?
        <ErrorState message={interventions.error} retry={interventions.reload} /> :
        interventions.data?.interventions.length ? <div className="run-list">
          {interventions.data.interventions.map((item) => item.intervention_id &&
            <NavLink className="run-row" to={`/interventions/${item.intervention_id}`} key={`${item.run_id}-${item.intervention_id}`}>
              <span className="square-icon warning-icon"><Hand size={17} /></span>
              <span><strong>{item.active ? "Live handoff" : "Recorded handoff"}</strong><small>{item.run_id}</small></span>
              <span>{item.capability_id}</span><StatusBadge status={item.state_label} /><time>{formatDate(item.created_at)}</time>
            </NavLink>)}</div> : <EmptyState icon={<Hand size={27} />} title="No interventions recorded"
              copy="Start Demo Handoff to pause the savings workflow for approval." />}
    </section>
  </div>;
}

function InterventionDetail({ interventionId }: { interventionId: string }) {
  const endpoint = `/api/interventions/${encodeURIComponent(interventionId)}`;
  const intervention = useApi<Intervention>(endpoint);
  const [current, setCurrent] = useState<Intervention | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [completion, setCompletion] = useState<string | null>(null);
  const [outputs, setOutputs] = useState<Record<string, string | number> | null>(null);
  const [viewRevision, setViewRevision] = useState(0);
  const [previewUnavailable, setPreviewUnavailable] = useState(false);
  const data = current ?? intervention.data;
  const live = Boolean(data?.active && !completion);
  useEffect(() => {
    if (!live || previewUnavailable) return;
    const interval = window.setInterval(() => setViewRevision((value) => value + 1), 2000);
    return () => window.clearInterval(interval);
  }, [live, previewUnavailable]);

  async function transition(kind: "take-control" | "focus-browser" | "return-control" | "stop") {
    setBusy(true); setMessage(null);
    try {
      const result = await apiRequest<Intervention & { status?: string; outputs?: Record<string, string | number> }>(`${endpoint}/${kind}`, { method: "POST" });
      if (kind === "take-control" || kind === "focus-browser") {
        setCurrent(result); setMessage(result.summary ?? "Switch to the Capability Runner managed browser window.");
        setPreviewUnavailable(false); setViewRevision((value) => value + 1);
      } else {
        const outcome = result.status ?? result.replay_result ?? result.control_state;
        setCurrent((previous) => ({ ...(previous ?? intervention.data!), active: false,
          generation: result.generation_after ?? previous?.generation }));
        setCompletion(outcome);
        setOutputs(outcome === "SUCCESS" ? result.outputs ?? null : null);
        setMessage(kind === "stop" ? "The session was stopped." : outcome === "SUCCESS" ?
          "Fresh browser validation passed. Replay completed without repeating earlier actions." :
          `Resume did not succeed: ${humanize(result.reason_code ?? outcome)}. The browser session was closed; start a new handoff to try again.`);
      }
    } catch (requestError) { setMessage(errorMessage(requestError)); }
    finally { setBusy(false); }
  }
  if (intervention.loading) return <LoadingState label="Loading intervention" />;
  if (intervention.error) return <ErrorState message={intervention.error} retry={intervention.reload} />;
  if (!data) return null;
  const human = data.control_state === "operator_controlled";
  const state = completion ?? data.state_label;
  return <div className="intervention-page page-enter">
    <div className="breadcrumbs"><NavLink to="/interventions"><ArrowLeft size={15} /> Interventions</NavLink><span>/</span><span>{data.run_id}</span></div>
    <div className="run-title"><div><h2>Run / {data.capability_id}</h2><p>Run ID: {data.run_id}</p></div><StatusBadge status={state} /></div>
    <section className="intervention-banner"><span><Hand size={30} /></span><div>
      <h3>{live ? "Human intervention required" : "Human intervention recorded"}</h3>
      <p>{data.reason ?? data.summary ?? "Approval is required before opening Savings."}</p>
      <small>{live ? "Automation is paused. Take control, click Open in the Savings row of the managed browser, then return control here." : "This historical record has no live browser session."}</small>
    </div></section>
    <div className="intervention-grid"><section className="panel live-surface">
      <div className="panel-heading"><h3>Managed browser preview</h3><span className="panel-count">Preview only</span></div>
      {live ? <div className="surface-frame"><div className="browser-chrome"><i /><i /><i /><span>Interact in the managed browser window</span></div>
        {previewUnavailable ? <p>Preview unavailable. If you closed the browser, return control to record the failure or stop the session.</p> :
          <img src={`${endpoint}/view?generation=${data.generation ?? 0}&revision=${viewRevision}`}
            alt="Read-only preview of the managed browser" onError={() => setPreviewUnavailable(true)} />}
      </div> : <div className="historical-surface"><h3>Live surface closed</h3><p>Review the run evidence for the recorded outcome.</p></div>}
    </section><aside className="panel intervention-details"><div className="panel-heading"><h3>Intervention Details</h3></div><dl>
      <div><dt>Application</dt><dd>{data.application ?? "CoreBank Legacy"}</dd></div>
      <div><dt>Current step</dt><dd>{data.blocked_action ?? "Open Savings"}</dd></div>
      <div><dt>Controller</dt><dd>{live ? (human ? "Human reviewer" : "Automation paused") : "Session closed"}</dd></div>
      <div><dt>Handoff state</dt><dd>{state}</dd></div>
      <div><dt>Generation</dt><dd>{data.generation ?? data.generation_after ?? "Recorded in evidence"}</dd></div>
      <div><dt>Surface session</dt><dd className="mono">{data.surface_session_id ?? "Recorded in evidence"}</dd></div>
      <div><dt>Replay result</dt><dd>{completion ?? data.replay_result ?? "Pending"}</dd></div>
      {outputs && <><div><dt>Balance (minor units)</dt><dd>{outputs.balance_minor_units}</dd></div>
        <div><dt>Currency</dt><dd>{outputs.currency}</dd></div></>}
    </dl><div className="audit-note"><span><strong>Direct browser handoff</strong><small>Human clicks happen in the browser. Passive observations are separate from gateway actions. Fresh state decides whether Replay can resume.</small></span></div></aside></div>
    {live && <section className="operator-bar"><div><strong>{human ? "You control the managed browser" : "Ready to transfer control"}</strong>
      <small>{data.browser_headless ? "Headless test mode: restart with CAPABILITY_RUNNER_BROWSER_HEADLESS=false for a visible browser." : "Switch to the Capability Runner managed browser window. Click Open in the Savings row, then return here."}</small></div>
      <div className="operator-actions">
        <button className="button button-secondary" type="button" disabled={busy} onClick={() => transition(human ? "focus-browser" : "take-control")}>
          <Hand size={17} />{human ? "Focus live browser" : "Take control"}</button>
        <button className="button button-primary" type="button" disabled={busy || !human} onClick={() => transition("return-control")}>
          <Check size={17} />Return control to automation</button>
        <button className="button button-danger" type="button" disabled={busy} onClick={() => transition("stop")}><Square size={15} />Stop</button>
      </div></section>}
    {message && <p role="status" className={completion && completion !== "SUCCESS" ? "inline-error" : "audit-note"}>{message}</p>}
  </div>;
}
