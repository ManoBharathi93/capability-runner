import { Activity, BookOpen, Boxes, Play, Search, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState, StatusBadge, formatDate } from "../components";
import { useApi } from "../useApi";
import type { Overview } from "../types";

export function HomePage() {
  const overview = useApi<Overview>("/api/overview");
  return (
    <div className="home-page page-enter">
      <section className="welcome-banner">
        <div>
          <p className="eyebrow">TURN EXPERTISE <span>INTO ACTION</span></p>
          <h2>Good morning, Operator</h2>
          <p>Automate enterprise workflows with trusted, reusable capabilities.</p>
        </div>
        <div className="banner-message">Trusted actions.<br />Verifiable outcomes.<i /></div>
      </section>
      <div className="home-layout">
        <div className="home-primary">
          <section className="action-grid" aria-label="Primary actions">
            <ActionCard icon={Search} title="Discover Workflow" copy="Discover and compile a reusable capability through the trusted model provider." action="Start Discovery" to="/discover" tone="blue" />
            <ActionCard icon={BookOpen} title="Teach Workflow" copy="Preview the future guided teaching surface without starting media capture." action="View Teach Surface" to="/teach" tone="violet" />
            <ActionCard icon={Play} title="Run Capability" copy="Execute the stored capability with deterministic, model-free Replay." action="Start a Run" to="/runs" tone="green" />
          </section>
          {overview.loading ? <LoadingState /> : overview.error ? <ErrorState message={overview.error} retry={overview.reload} /> : overview.data && (
            <>
              <section className="metric-grid" aria-label="Workspace summary">
                <Metric label="Active Runs" value={overview.data.active_run_count} note="Current server process" icon={Play} />
                <Metric label="Capabilities" value={overview.data.capability_count} note="Validated artifacts" icon={Boxes} />
                <Metric label="Interventions" value={overview.data.intervention_count} note="Recorded handoffs" icon={Activity} />
                <Metric label="Verified Runs" value={overview.data.verified_run_count} note={`${overview.data.run_count} total records`} icon={ShieldCheck} />
              </section>
              <section className="panel recent-panel">
                <div className="panel-heading"><h3>Recent Runs</h3><NavLink to="/runs">View all →</NavLink></div>
                {overview.data.recent_runs.length ? (
                  <div className="data-table recent-table">
                    <div className="table-row table-head"><span>Run</span><span>Capability</span><span>Status</span><span>Recorded</span></div>
                    {overview.data.recent_runs.map((run) => (
                      <NavLink className="table-row" to={`/runs/${run.run_id}`} key={run.run_id}>
                        <strong>{run.demo_kind.replaceAll("-", " ")}</strong><span>{run.capability_id ?? "No capability"}</span><StatusBadge status={run.replay_result ?? run.status} /><span>{formatDate(run.created_at)}</span>
                      </NavLink>
                    ))}
                  </div>
                ) : <EmptyState icon={<Play size={24} />} title="No runs recorded" copy="Complete a real Discovery or Replay to populate this history." />}
              </section>
            </>
          )}
        </div>
        <aside className="home-aside">
          <section className="panel status-panel">
            <h3>System Health</h3>
            <div className="unavailable-state"><span />Runtime telemetry unavailable</div>
            <p>No health service is configured for this local review build.</p>
            <dl><div><dt>Execution Engine</dt><dd>On demand</dd></div><div><dt>Model Services</dt><dd>Not probed</dd></div><div><dt>Data Connectors</dt><dd>Not configured</dd></div><div><dt>Storage</dt><dd>Local artifacts</dd></div></dl>
          </section>
          <section className="panel environment-panel">
            <div className="panel-heading"><h3>Environment</h3><StatusBadge status="Local review" /></div>
            <dl><div><dt>Data source</dt><dd>Sanitized artifacts</dd></div><div><dt>Provider</dt><dd>Server managed</dd></div><div><dt>Secrets</dt><dd>Never exposed</dd></div></dl>
          </section>
        </aside>
      </div>
    </div>
  );
}

function ActionCard({ icon: Icon, title, copy, action, to, tone }: { icon: typeof Search; title: string; copy: string; action: string; to: string; tone: string }) {
  return <article className={`action-card ${tone}`}><div className="action-icon"><Icon size={26} /></div><h3>{title}</h3><p>{copy}</p><NavLink className="button button-primary" to={to}>{action}<span aria-hidden="true">→</span></NavLink></article>;
}

function Metric({ label, value, note, icon: Icon }: { label: string; value: number; note: string; icon: typeof Play }) {
  return <article className="metric-card"><div className="metric-icon"><Icon size={18} /></div><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div></article>;
}