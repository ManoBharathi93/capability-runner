import { Activity, ArrowLeft, Check, Circle, Clock, FileText, Play, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { NavLink, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { apiRequest, errorMessage } from "../api";
import { EmptyState, ErrorState, LoadingState, StatusBadge, formatDate, humanize } from "../components";
import { useApi } from "../useApi";
import type { Capability, EvidenceEvent, RunSummary } from "../types";

export function RunsPage() {
  const { runId } = useParams();
  return runId ? <RunDetail runId={runId} /> : <RunList />;
}

function RunList() {
  const runs = useApi<{ runs: RunSummary[] }>("/api/runs");
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [memberId, setMemberId] = useState("");
  const [showValue, setShowValue] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const capabilityId = searchParams.get("capability") ?? "lookup_savings_balance";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await apiRequest<{ run: RunSummary }>("/api/replay", { method: "POST", body: JSON.stringify({ capability_id: capabilityId, version: "1.0.0", member_id: memberId }) });
      navigate(`/runs/${result.run.run_id}`);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSubmitting(false);
      setMemberId("");
    }
  }

  return <div className="page-stack page-enter"><section className="page-title"><div><p className="eyebrow">MODEL-FREE EXECUTION</p><h2>Runs</h2><p>Execute a validated capability or inspect sanitized local run evidence.</p></div></section>{capabilityId.startsWith("workflow_") ? <GeneratedReplayForm capabilityId={capabilityId} /> : <section className="panel run-launcher"><div><h3>Run {capabilityId}</h3><p>A fresh browser session executes the stored steps without model decisions.</p></div><form onSubmit={submit}><label>Member ID<div className="input-with-action"><input required type={showValue ? "text" : "password"} value={memberId} onChange={(event) => setMemberId(event.target.value)} autoComplete="off" /><button type="button" onClick={() => setShowValue((value) => !value)}>{showValue ? "Hide" : "Show"}</button></div></label><button className="button button-primary" disabled={submitting} type="submit"><Play size={16} />{submitting ? "Running..." : "Start Replay"}</button></form>{error && <p className="inline-error">{error}</p>}</section>}<section className="panel"><div className="panel-heading"><h3>Run History</h3><span className="panel-count">{runs.data?.runs.length ?? 0} actual records</span></div>{runs.loading ? <LoadingState /> : runs.error ? <ErrorState message={runs.error} retry={runs.reload} /> : runs.data?.runs.length ? <div className="run-list">{runs.data.runs.map((run) => <NavLink to={`/runs/${run.run_id}`} className="run-row" key={run.run_id}><span className="square-icon"><Play size={17} /></span><span><strong>{humanize(run.demo_kind)}</strong><small>{run.run_id}</small></span><span>{run.capability_id ?? "No capability"}</span><StatusBadge status={run.replay_result ?? run.status} /><time>{formatDate(run.created_at)}</time></NavLink>)}</div> : <EmptyState icon={<Play size={26} />} title="No runs recorded" copy="Start a real Replay to create the first record." />}</section></div>;
}

function RunDetail({ runId }: { runId: string }) {
  const run = useApi<RunSummary>(`/api/runs/${encodeURIComponent(runId)}`);
  const events = useApi<{ events: EvidenceEvent[] }>(`/api/runs/${encodeURIComponent(runId)}/events`);
  if (run.loading || events.loading) return <LoadingState label="Loading run evidence" />;
  if (run.error) return <ErrorState message={run.error} retry={run.reload} />;
  if (events.error) return <ErrorState message={events.error} retry={events.reload} />;
  if (!run.data || !events.data) return null;
  const eventItems = Array.isArray(events.data.events) ? events.data.events : [];
  const lifecycle = eventItems.filter((event) => event.event_type === "lifecycle" || event.event_type === "outcome");
  const steps = Array.from(new Map(eventItems.filter((event) => event.step_id).map((event) => [event.step_id, event])).values()).slice(0, 5);
  return <div className="run-detail-page page-enter"><div className="breadcrumbs"><NavLink to="/runs"><ArrowLeft size={15} /> Runs</NavLink><span>›</span><span>{run.data.capability_id ?? humanize(run.data.demo_kind)}</span></div><section className="run-title"><div><h2>Run / {run.data.capability_id ?? humanize(run.data.demo_kind)}</h2><p>{run.data.run_id} · Recorded {formatDate(run.data.created_at)}</p></div><StatusBadge status={run.data.replay_result ?? run.data.status} /></section><section className="panel progress-strip">{(steps.length ? steps : [{ step_id: "run", reason_code: run.data.status } as EvidenceEvent]).map((step, index) => <div className="progress-step" key={step.step_id ?? index}><span><Check size={14} /></span><strong>{step.step_id ? humanize(step.step_id) : "Run"}</strong><small>{step.reason_code ? humanize(step.reason_code) : "Recorded"}</small></div>)}</section><div className="run-detail-grid"><section className="panel execution-panel"><div className="panel-heading"><h3><FileText size={19} /> Execution Evidence</h3><StatusBadge status="Sanitized" /></div><div className="execution-summary"><div className="execution-watermark"><ShieldCheck size={48} /><strong>Verified local evidence</strong><span>No raw browser DOM, selectors, prompts, or model payloads are exposed.</span></div><dl>{Object.entries(run.data.outputs ?? {}).map(([name, value]) => <div key={name}><dt>{humanize(name)}</dt><dd>{String(value)}</dd></div>)}{run.data.business_outcome && <div><dt>Business outcome</dt><dd>{humanize(run.data.business_outcome)}</dd></div>}{run.data.failure_reason && <div><dt>Failure reason</dt><dd>{humanize(run.data.failure_reason)}</dd></div>}<div><dt>Browser actions</dt><dd>{run.data.browser_action_count ?? "Unavailable"}</dd></div><div><dt>Replay model calls</dt><dd>{run.data.replay_model_calls ?? "Unavailable"}</dd></div></dl></div></section><aside className="panel activity-panel"><div className="panel-heading"><h3><Activity size={19} /> Agent Activity</h3></div><div className="timeline">{lifecycle.length ? lifecycle.map((event) => <article key={event.event_id}><span className={`timeline-dot ${event.outcome === "success" || event.outcome === "completed" ? "done" : ""}`}>{event.outcome === "success" || event.outcome === "completed" ? <Check size={11} /> : <Circle size={10} />}</span><div><strong>{humanize(event.reason_code ?? event.event_type)}</strong><small>{event.component}{event.step_id ? ` · ${humanize(event.step_id)}` : ""}</small></div><time>{new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</time></article>) : <EmptyState icon={<Clock size={23} />} title="No event records" copy="This run has no persisted timeline." />}</div></aside></div></div>;
}

function GeneratedReplayForm({ capabilityId }: { capabilityId: string }) {
  const capability = useApi<Capability>(`/api/capabilities/${encodeURIComponent(capabilityId)}`);
  const navigate = useNavigate();
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!capability.data) return;
    setBusy(true); setError(null);
    try {
      const result = await apiRequest<{ run: RunSummary }>("/api/replay", { method: "POST",
        body: JSON.stringify({ capability_id: capabilityId, version: capability.data.version, inputs }) });
      navigate(`/runs/${result.run.run_id}`);
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setBusy(false); setInputs({}); }
  }
  if (capability.loading) return <LoadingState label="Loading capability inputs" />;
  if (capability.error || !capability.data) return <ErrorState message={capability.error ?? "Capability unavailable"} />;
  return <section className="panel run-launcher"><div><h3>Run {capability.data.name}</h3>
    <p>A fresh browser loads the stored workflow and application binding. No model calls.</p></div>
    <form onSubmit={submit}>{capability.data.definition.inputs.map(input => <label key={input.name}>
      {humanize(input.name)}<input type={input.sensitive ? "password" : "text"} required={input.required}
        value={inputs[input.name] ?? ""} maxLength={128} autoComplete="off"
        onChange={event => setInputs({ ...inputs, [input.name]: event.target.value })} /></label>)}
      <button className="button button-primary" disabled={busy} type="submit">Start Replay</button></form>
    {error && <p className="inline-error">{error}</p>}</section>;
}
