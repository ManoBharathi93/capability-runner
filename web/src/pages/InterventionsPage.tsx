import { AlertCircle, ArrowLeft, Check, ExternalLink, Hand, Play, ShieldCheck, Square } from "lucide-react";
import { useState } from "react";
import { NavLink, useNavigate, useParams } from "react-router-dom";

import { apiRequest, errorMessage } from "../api";
import { EmptyState, ErrorState, LoadingState, StatusBadge, SuccessMark, formatDate, humanize } from "../components";
import { useApi } from "../useApi";
import type { Intervention, OperatorControl } from "../types";

export function InterventionsPage() {
  const { interventionId } = useParams();
  return interventionId ? <InterventionDetail interventionId={interventionId} /> : <InterventionList />;
}

function InterventionList() {
  const interventions = useApi<{ interventions: Intervention[] }>("/api/interventions");
  const navigate = useNavigate();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function start() {
    setStarting(true); setError(null);
    try { const result = await apiRequest<Intervention>("/api/interventions", { method: "POST" }); navigate(`/interventions/${result.intervention_id}`); }
    catch (requestError) { setError(errorMessage(requestError)); }
    finally { setStarting(false); }
  }
  return <div className="page-stack page-enter"><section className="page-title split"><div><p className="eyebrow">SAME-SESSION HANDOFF</p><h2>Human Interventions</h2><p>Review actual approval handoffs and control only a currently managed browser session.</p></div><button className="button button-primary" type="button" onClick={start} disabled={starting}><Hand size={17} />{starting ? "Opening..." : "Start Demo Handoff"}</button></section>{error && <p className="inline-error">{error}</p>}<section className="panel"><div className="panel-heading"><h3>Intervention History</h3></div>{interventions.loading ? <LoadingState /> : interventions.error ? <ErrorState message={interventions.error} retry={interventions.reload} /> : interventions.data?.interventions.length ? <div className="run-list">{interventions.data.interventions.map((item) => item.intervention_id && <NavLink className="run-row" to={`/interventions/${item.intervention_id}`} key={`${item.run_id}-${item.intervention_id}`}><span className="square-icon warning-icon"><Hand size={17} /></span><span><strong>{item.active ? "Live handoff" : "Recorded handoff"}</strong><small>{item.run_id}</small></span><span>{item.capability_id}</span><StatusBadge status={item.state_label} /><time>{formatDate(item.created_at)}</time></NavLink>)}</div> : <EmptyState icon={<Hand size={27} />} title="No interventions recorded" copy="Start the real H-02 handoff to create one." />}</section></div>;
}

function InterventionDetail({ interventionId }: { interventionId: string }) {
  const intervention = useApi<Intervention>(`/api/interventions/${encodeURIComponent(interventionId)}`);
  const controls = useApi<{ controls: OperatorControl[] }>(intervention.data?.active ? `/api/interventions/${encodeURIComponent(interventionId)}/controls` : null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [finished, setFinished] = useState(false);
  const [completionStatus, setCompletionStatus] = useState<string | null>(null);
  const [viewRevision, setViewRevision] = useState(0);
  async function act(control: OperatorControl, value?: string) {
    setBusy(true); setMessage(null);
    try { const result = await apiRequest<{ summary?: string }>(`/api/interventions/${encodeURIComponent(interventionId)}/actions`, { method: "POST", body: JSON.stringify({ semantic_target: control.semantic_target, action_kind: control.action_kind, ...(value ? { value } : {}) }) }); setMessage(result.summary ?? `${control.label} completed.`); setViewRevision((value) => value + 1); controls.reload(); }
    catch (requestError) { setMessage(errorMessage(requestError)); }
    finally { setBusy(false); }
  }
  async function transition(kind: "return-control" | "stop") {
    setBusy(true); setMessage(null);
    try { const result = await apiRequest<{ replay_result?: string; status?: string; control_state?: string }>(`/api/interventions/${encodeURIComponent(interventionId)}/${kind}`, { method: "POST" }); setFinished(true); setCompletionStatus(result.replay_result ?? result.status ?? result.control_state ?? "COMPLETED"); setMessage(kind === "return-control" ? "Control returned. Replay completed after fresh validation." : "The intervention session was stopped."); }
    catch (requestError) { setMessage(errorMessage(requestError)); }
    finally { setBusy(false); }
  }
  if (intervention.loading) return <LoadingState label="Loading intervention" />;
  if (intervention.error) return <ErrorState message={intervention.error} retry={intervention.reload} />;
  if (!intervention.data) return null;
  const live = intervention.data.active && !finished;
  const displayedState = finished ? (completionStatus === "terminal" ? "Session stopped" : "Completed intervention") : intervention.data.state_label;
  const displayedResult = completionStatus ?? intervention.data.replay_result ?? (live ? "Pending" : "Unavailable");
  return <div className="intervention-page page-enter"><div className="breadcrumbs"><NavLink to="/interventions"><ArrowLeft size={15} /> Interventions</NavLink><span>›</span><span>{intervention.data.run_id}</span></div><div className="run-title"><div><h2>Run / {intervention.data.capability_id}</h2><p>Run ID: {intervention.data.run_id}</p></div><StatusBadge status={live ? "Paused" : displayedState} /></div><section className="intervention-banner"><span><Hand size={30} /></span><div><h3>{live ? "Human intervention required" : "Human intervention recorded"}</h3><p>{intervention.data.reason ?? intervention.data.summary ?? "A trusted semantic action required operator approval."}</p><small>{live ? "Use only the available semantic controls. Replay resumes after fresh state validation." : "This historical record has no live browser session."}</small></div>{live && <button className="button button-primary" type="button" onClick={() => document.getElementById("operator-controls")?.scrollIntoView({ behavior: "smooth" })}><Play size={17} fill="currentColor" /> Take Control</button>}</section><div className="intervention-grid"><section className="panel live-surface"><div className="panel-heading"><h3>Live Browser Session</h3>{live ? <span className="secure-label"><span /> Secure active session</span> : <span className="panel-count">Historical record</span>}</div>{live ? <div className="surface-frame"><div className="browser-chrome"><i /><i /><i /><span>Managed CoreBank surface</span><ExternalLink size={15} /></div><img src={`/api/interventions/${encodeURIComponent(interventionId)}/view?generation=${intervention.data.generation ?? 0}&revision=${viewRevision}`} alt="Current managed browser surface" /></div> : <div className="historical-surface"><ShieldCheck size={46} /><h3>Live surface closed</h3><p>Browser imagery is never persisted. The safe handoff context remains available at right.</p></div>}</section><aside className="panel intervention-details"><div className="panel-heading"><h3>Intervention Details</h3></div><dl><div><dt><AlertCircle size={18} /> Reason</dt><dd>{humanize(intervention.data.reason_code)}</dd></div><div><dt><Square size={18} /> Blocked action</dt><dd>{intervention.data.blocked_action ?? "Unavailable"}</dd></div><div><dt><ShieldCheck size={18} /> Handoff state</dt><dd>{displayedState}</dd></div><div><dt><Check size={18} /> Replay result</dt><dd>{displayedResult}</dd></div></dl><div className="audit-note"><ShieldCheck size={22} /><span><strong>Secure, audited session</strong><small>Actions pass through Action Gateway. Sensitive values are never echoed.</small></span></div></aside></div>{live ? <section id="operator-controls" className="operator-bar"><div><strong>Complete the trusted action, then return control</strong><small>{message ?? "Only controls visible in the current browser state are available."}</small></div><div className="operator-actions">{controls.data?.controls.map((control) => control.action_kind === "click" ? <button key={control.semantic_target} className="button button-secondary" disabled={busy} type="button" onClick={() => act(control)}>{control.label}</button> : <SensitiveControl key={control.semantic_target} control={control} disabled={busy} submit={act} />)}<button className="button button-primary" type="button" disabled={busy} onClick={() => transition("return-control")}><Check size={17} /> Return Control to Agent</button><button className="button button-danger" type="button" disabled={busy} onClick={() => transition("stop")}><Square size={15} /> Stop</button></div></section> : message && <section className="operator-bar completion-bar"><SuccessMark /><div><strong>{displayedResult}</strong><small>{message}</small></div></section>}</div>;
}

function SensitiveControl({ control, disabled, submit }: { control: OperatorControl; disabled: boolean; submit: (control: OperatorControl, value?: string) => void }) {
  const [value, setValue] = useState("");
  return <label className="compact-control"><span>{control.label}</span><input type="password" value={value} onChange={(event) => setValue(event.target.value)} autoComplete="off" /><button className="button button-secondary" type="button" disabled={disabled || !value} onClick={() => { submit(control, value); setValue(""); }}>Submit</button></label>;
}
