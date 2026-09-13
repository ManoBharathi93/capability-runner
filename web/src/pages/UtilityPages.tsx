import { BookOpen, FileText, MicOff, MonitorOff, Radio, Settings, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState, StatusBadge, formatDate } from "../components";
import { useApi } from "../useApi";
import type { Intervention, RunSummary } from "../types";

export function TeachPage() {
  return <div className="teach-page page-enter"><section className="teach-stage"><div className="teach-copy"><p className="eyebrow">VISUAL PREVIEW · P6 NOT STARTED</p><h2>Teach a workflow</h2><p>This screen preserves the intended product experience without connecting microphone, voice, screen share, or a teaching session.</p><div className="teach-controls"><button type="button" disabled><MicOff size={22} /><span>Microphone<strong>Not connected</strong></span></button><button type="button" disabled><MonitorOff size={22} /><span>Screen share<strong>Not connected</strong></span></button></div></div><div className="teach-visual"><span><BookOpen size={48} /></span><div className="signal-lines"><i /><i /><i /><i /></div><strong>Teaching surface ready for a future phase</strong><small>No media device has been accessed.</small></div></section></div>;
}

export function SessionsPage() {
  const interventions = useApi<{ interventions: Intervention[] }>("/api/interventions");
  if (interventions.loading) return <LoadingState label="Loading current sessions" />;
  if (interventions.error) return <ErrorState message={interventions.error} retry={interventions.reload} />;
  const active = interventions.data?.interventions.filter((item) => item.active) ?? [];
  return <div className="page-stack page-enter">
    <section className="page-title split">
      <div><p className="eyebrow">LIVE HANDOFFS</p><h2>Sessions</h2>
        <p>Active intervention sessions appear here. Discovery runs are shown on Discover and Runs.</p></div>
      <div className="artifact-actions">
        <button className="button button-secondary" type="button" onClick={interventions.reload}>Refresh sessions</button>
        <NavLink className="button button-primary" to="/interventions">Open Interventions</NavLink>
      </div>
    </section>
    <section className="panel">{active.length ? <div className="run-list">{active.map((item) =>
      <NavLink className="run-row" to={`/interventions/${item.intervention_id}`} key={item.intervention_id}>
        <span className="square-icon"><Radio size={17} /></span>
        <span><strong>{item.state_label}</strong><small>{item.run_id}</small>
          <small>Session: {item.surface_session_id ?? "Unavailable"}</small>
          <small>Controller: {item.owner_kind ?? "unknown"} · generation {item.generation ?? "unknown"}</small></span>
        <span>{item.application ?? item.capability_id}</span>
        <StatusBadge status={item.control_state ?? "Active"} />
      </NavLink>)}</div> : <EmptyState icon={<Radio size={27} />} title="No active sessions"
        copy="Open Interventions and choose Start Demo Handoff to begin. Completed or stopped sessions remain in intervention history." />}
    </section>
  </div>;
}

export function EvidencePage() {
  const runs = useApi<{ runs: RunSummary[] }>("/api/runs");
  return <div className="page-stack page-enter"><section className="page-title"><p className="eyebrow">SANITIZED EVIDENCE</p><h2>Evidence</h2><p>Lifecycle, action, policy, outcome, error, and intervention events from actual local runs.</p></section><section className="panel"><div className="panel-heading"><h3>Evidence Sets</h3></div>{runs.loading ? <LoadingState /> : runs.error ? <ErrorState message={runs.error} retry={runs.reload} /> : runs.data?.runs.length ? <div className="run-list">{runs.data.runs.map((run) => <NavLink className="run-row" to={`/runs/${run.run_id}`} key={run.run_id}><span className="square-icon"><FileText size={17} /></span><span><strong>{run.run_id}</strong><small>{run.event_count} safe events</small></span><span>{run.capability_id ?? run.demo_kind}</span><StatusBadge status={run.status} /><time>{formatDate(run.created_at)}</time></NavLink>)}</div> : <EmptyState icon={<FileText size={27} />} title="No evidence sets" copy="Completed runs create sanitized evidence automatically." />}</section></div>;
}

export function SettingsPage() {
  return <div className="page-stack page-enter"><section className="page-title"><p className="eyebrow">LOCAL REVIEW CONFIGURATION</p><h2>Settings</h2><p>Nonsecret client and runtime boundaries for this product surface.</p></section><section className="settings-grid"><article className="panel setting-card"><Settings size={22} /><div><h3>Runtime mode</h3><p>Local demo composition</p></div><StatusBadge status="Local review" /></article><article className="panel setting-card"><ShieldCheck size={22} /><div><h3>Evidence policy</h3><p>Sanitized structured events only</p></div><StatusBadge status="Enforced" /></article><article className="panel setting-card"><MonitorOff size={22} /><div><h3>Teaching media</h3><p>Voice and screen share remain outside P5.4b</p></div><StatusBadge status="Disabled" /></article></section></div>;
}
