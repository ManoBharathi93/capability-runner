import { Check, Compass, LockKeyhole, Monitor, Play, Sparkles } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

import { apiRequest, errorMessage } from "../api";
import { StatusBadge, humanize } from "../components";
import type { CapabilityInput, CapabilityOutput, CapabilityStep, EvidenceEvent } from "../types";

type Definition = {
  capability_id: string; capability_version: string; name: string;
  inputs: CapabilityInput[]; outputs: CapabilityOutput[]; steps: CapabilityStep[];
  success_conditions: unknown[]; business_outcomes: unknown[];
};
type Replay = {
  outcome: string; reason_code?: string; business_outcome_code?: string;
  outputs: Record<string, string | number>; replay_model_calls: number;
};
type Workspace = {
  run_id: string; status: string; reason_code: string | null; application: string;
  session_id: string | null; model_calls: number; actions: number; view_available: boolean;
  events: EvidenceEvent[]; capability: Definition | null; binding: unknown;
};

function SurfacePreview({ run }: { run: Workspace | null }) {
  const [frame, setFrame] = useState<string | null>(null);
  useEffect(() => {
    if (!run?.view_available) { setFrame(null); return; }
    let disposed = false;
    let current: string | null = null;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const refresh = async () => {
      try {
        const response = await fetch(`/api/discovery/${encodeURIComponent(run.run_id)}/view`, {
          cache: "no-store", signal: controller.signal,
        });
        if (response.ok) {
          const blob = await response.blob();
          if (!disposed) {
            const next = URL.createObjectURL(blob);
            setFrame(next);
            if (current) URL.revokeObjectURL(current);
            current = next;
          }
        }
      } catch { /* Transient view errors do not change backend run status. */ }
      if (!disposed && run.status === "RUNNING") timer = setTimeout(refresh, 1000);
    };
    void refresh();
    return () => { disposed = true; controller.abort(); clearTimeout(timer); if (current) URL.revokeObjectURL(current); };
  }, [run?.run_id, run?.view_available, run?.status]);
  return <section className="panel live-surface discovery-preview">
    <div className="panel-heading"><div><h3><Monitor size={19} /> Live application</h3>
      <p>The same managed browser Discovery is using</p></div>
      <span className="panel-count">Read-only preview</span></div>
    <div className="surface-frame"><div className="browser-chrome"><i /><i /><i />
      <span>{run ? humanize(run.application) : "Managed legacy web application"}</span></div>
      {frame ? <img src={frame} alt="Live legacy application in the current Discovery session" /> :
        <div className="preview-placeholder"><Monitor size={38} /><h3>{run ? "Connecting to the managed browser" : "Your workflow, in view"}</h3>
          <p>Submit a goal to watch Discovery observe and interact with the application.</p></div>}
    </div>
  </section>;
}

export function DiscoverPage() {
  const [goal, setGoal] = useState("");
  const [application, setApplication] = useState("corebank-known");
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<Workspace | null>(null);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [replay, setReplay] = useState<Replay | null>(null);
  const [replaying, setReplaying] = useState(false);
  useEffect(() => {
    if (!run || run.status !== "RUNNING") return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const result = await apiRequest<Workspace>(`/api/discovery/${encodeURIComponent(run.run_id)}`);
        if (!disposed) { setRun(result); if (result.status === "RUNNING") timer = setTimeout(poll, 900); }
      } catch (requestError) { if (!disposed) setError(errorMessage(requestError)); }
    };
    timer = setTimeout(poll, 500);
    return () => { disposed = true; clearTimeout(timer); };
  }, [run?.run_id, run?.status]);
  async function submit(event: FormEvent) {
    event.preventDefault(); setSubmitting(true); setError(null); setRun(null); setReplay(null); setInputs({});
    try { setRun(await apiRequest<Workspace>("/api/discovery", {
      method: "POST", body: JSON.stringify({ goal, application, ...(application === "new" ? { url } : {}) }),
    })); } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setSubmitting(false); }
  }
  async function startReplay(event: FormEvent) {
    event.preventDefault(); if (!run) return;
    setReplaying(true); setError(null); setReplay(null);
    try { setReplay(await apiRequest<Replay>(`/api/discovery/${encodeURIComponent(run.run_id)}/replay`, {
      method: "POST", body: JSON.stringify({ inputs }),
    })); setInputs({}); } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setReplaying(false); }
  }
  const running = submitting || run?.status === "RUNNING";
  const lifecycle = run?.events.filter(event => event.event_type === "lifecycle" || event.event_type === "action") ?? [];
  const definition = run?.capability;
  const validUrl = application !== "new" || /^https?:\/\/[^\s]+$/i.test(url);
  return <div className="discover-page page-enter">
    <section className="workspace-heading"><span className="discover-orbit"><Compass size={26} /></span>
      <div><p className="eyebrow">DISCOVER</p><h2>Turn a workflow into a capability</h2>
        <p>Describe an outcome. Watch Discovery explore, then replay the saved workflow without a model.</p></div>
    </section>
    <div className="discovery-workspace">
      <aside className="discovery-sidebar">
        <form className="panel discovery-form" onSubmit={submit}>
          <label>Application<select aria-label="Application" value={application} disabled={running} onChange={event => setApplication(event.target.value)}>
            <option value="corebank-known">CoreBank Legacy · known profile</option>
            <option value="corebank">CoreBank Legacy · new-app discovery</option>
            <option value="bank-b">LegacyBank B · new-app discovery</option>
            <option value="new">New legacy web app</option>
          </select></label>
          {application === "new" && <label>Application URL<input type="url" value={url} onChange={event => setUrl(event.target.value)} placeholder="https://allowed-sandbox.example/" required /></label>}
          <label>Workflow goal<textarea value={goal} onChange={event => setGoal(event.target.value)} rows={4} maxLength={4000}
            placeholder="Describe the information you want to find…" /></label>
          <small className="form-footnote">{goal.length} / 4,000 characters</small>
          <button className="button button-primary" type="submit" disabled={running || !goal.trim() || goal.length > 4000 || !validUrl}>
            <Sparkles size={17} />{running ? "Discovering…" : "Discover Capability"}</button>
          <div className="trust-note"><LockKeyhole size={17} /><small>Bounded browser actions. Application access follows the configured read-only sandbox policy.</small></div>
        </form>
        <section className="panel discovery-activity"><div className="panel-heading"><h3>Discovery lifecycle</h3>{run && <StatusBadge status={run.status} />}</div>
          {lifecycle.length ? <div className="milestone-list">{lifecycle.map(event => <article key={event.event_id}>
            <span><Check size={13} /></span><div><strong>{event.event_type === "action" ? `${humanize(String(event.metadata.action_kind ?? "Action"))} ${humanize(String(event.metadata.semantic_target ?? "").split(".").at(-1) ?? "")}` : humanize(event.reason_code ?? "Observing")}</strong>
              <small>{event.event_type === "action" ? humanize(event.outcome ?? "") : event.metadata.decision_kind ? humanize(String(event.metadata.decision_kind)) : event.component}</small></div>
          </article>)}</div> : <p className="activity-empty">{running ? "Opening the managed browser…" : "Ready when you are. No model call until you submit."}</p>}
          {run?.reason_code && run.status !== "SUCCESS" && run.status !== "RUNNING" && <p className="inline-error">{humanize(run.reason_code)}</p>}
        </section>
      </aside>
      <div className="discovery-main"><SurfacePreview run={run} />
        {definition && <section className="panel generated-artifact"><div className="panel-heading"><div><p className="eyebrow">CAPABILITY CREATED</p><h3>{definition.name}</h3></div><StatusBadge status="SUCCESS" /></div>
          <div className="artifact-stats"><span>Version <strong>{definition.capability_version}</strong></span><span>Inputs <strong>{definition.inputs.length}</strong></span><span>Outputs <strong>{definition.outputs.length}</strong></span><span>Steps <strong>{definition.steps.length}</strong></span></div>
          <div className="artifact-actions"><NavLink className="button button-secondary" to={`/capabilities/${definition.capability_id}`}>View capability</NavLink>
            <a className="button button-primary" href="#discovery-replay"><Play size={15} /> Replay with new input</a></div>
          <details><summary>Typed capability · inputs, outputs, semantic steps and conditions</summary><pre>{JSON.stringify(definition, null, 2)}</pre></details>
          <details><summary>Application binding · deterministic browser resolution</summary><pre>{JSON.stringify(run.binding, null, 2)}</pre></details>
          <form id="discovery-replay" className="discovery-replay" onSubmit={startReplay}><h3>Replay with another input</h3>
            {definition.inputs.map(input => <label key={input.name}>{humanize(input.name)}<input type={input.sensitive ? "password" : "text"} value={inputs[input.name] ?? ""}
              onChange={event => setInputs({ ...inputs, [input.name]: event.target.value })} autoComplete="off" maxLength={128} required={input.required} /></label>)}
            <button className="button button-primary" disabled={replaying} type="submit"><Play size={16} />{replaying ? "Replaying…" : "Run Replay"}</button>
          </form>
          {replay && <div className="replay-outcome"><StatusBadge status={replay.outcome} /><div className="zero-model">Replay model calls <strong>{replay.replay_model_calls}</strong></div>
            {Object.entries(replay.outputs).map(([name, value]) => <p key={name}>{humanize(name)} <strong>{value}</strong></p>)}
            {replay.business_outcome_code && <p><strong>{replay.business_outcome_code}</strong><br />An expected application state is a business outcome, separate from an automation failure.</p>}
            {replay.reason_code && <p>{humanize(replay.reason_code)}</p>}</div>}
        </section>}
      </div>
    </div>
    {error && <p role="alert" className="inline-error">{error}</p>}
    <p className="workspace-truth">Active runs and browser sessions belong to this server process. Preview frames are transient; generated packages are stored locally.</p>
  </div>;
}
