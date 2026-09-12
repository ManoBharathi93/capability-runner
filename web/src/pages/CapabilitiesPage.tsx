import { Boxes, ChevronRight, Database, FileText, Filter, History, Play, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState, StatusBadge, humanize } from "../components";
import { useApi } from "../useApi";
import type { Capability } from "../types";

export function CapabilitiesPage() {
  const { capabilityId } = useParams();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("query") ?? "");
  const capabilities = useApi<{ capabilities: Capability[] }>("/api/capabilities");
  const navigate = useNavigate();
  const capabilityItems = Array.isArray(capabilities.data?.capabilities) ? capabilities.data.capabilities : [];
  const filtered = capabilityItems.filter((item) => `${item.name} ${item.description}`.toLowerCase().includes(query.toLowerCase()));
  const selected = filtered.find((item) => item.capability_id === capabilityId) ?? filtered[0] ?? null;

  useEffect(() => {
    if (!capabilityId && selected) navigate(`/capabilities/${selected.capability_id}`, { replace: true });
  }, [capabilityId, navigate, selected]);

  if (capabilities.loading) return <LoadingState label="Loading capability library" />;
  if (capabilities.error) return <ErrorState message={capabilities.error} retry={capabilities.reload} />;
  return (
    <div className="library-layout page-enter">
      <section className="panel library-panel">
        <div className="library-title"><div><h2>Capabilities Library</h2><p>Reusable, validated capability artifacts available to Replay.</p></div><button className="button button-primary" type="button" disabled title="Creation is performed through Discovery">+ New Capability</button></div>
        <div className="library-tools"><div className="segmented"><button className="active" type="button">All</button><button type="button" disabled>My Capabilities</button><button type="button" disabled>Shared</button></div><label className="search-input"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search capabilities..." /></label><button className="button button-secondary" type="button" disabled><Filter size={16} /> Filters</button></div>
        {!filtered.length ? <EmptyState icon={<Boxes size={28} />} title="No capabilities found" copy="Run Discovery to create a validated capability artifact." /> : (
          <div className="capability-list">
            <div className="capability-row capability-head"><span>Name</span><span>Version</span><span>Status</span><span>Details</span><span /></div>
            {filtered.map((capability) => (
              <NavLink className={({ isActive }) => `capability-row ${isActive ? "selected" : ""}`} to={`/capabilities/${capability.capability_id}`} key={`${capability.capability_id}-${capability.version}`}>
                <span className="capability-name"><i><Database size={20} /></i><span><strong>{capability.name}</strong><small>{capability.description}</small></span></span>
                <span>v{capability.version}</span><StatusBadge status={capability.status} /><span className="detail-chips"><i>{capability.input_count} input{capability.input_count === 1 ? "" : "s"}</i><i>{capability.output_count} output{capability.output_count === 1 ? "" : "s"}</i></span><ChevronRight size={17} />
              </NavLink>
            ))}
          </div>
        )}
      </section>
      <CapabilityDetail capability={selected} />
    </div>
  );
}

function CapabilityDetail({ capability }: { capability: Capability | null }) {
  if (!capability) return <aside className="panel detail-panel"><EmptyState icon={<Boxes size={25} />} title="No capability selected" copy="Select an available capability." /></aside>;
  return (
    <aside className="panel detail-panel">
      <div className="detail-title"><div className="square-icon"><Database size={24} /></div><div><h3>{capability.name}</h3><p>v{capability.version} <StatusBadge status={capability.status} /></p></div></div>
      <p className="detail-description">{capability.description}</p>
      <NavLink className="button button-primary full-button" to={`/runs?capability=${capability.capability_id}`}><Play size={17} fill="currentColor" /> Run Capability</NavLink>
      <div className="detail-actions"><NavLink to="/evidence"><FileText size={16} /> View Evidence</NavLink><span><History size={16} /> {capability.step_count} steps</span></div>
      <DefinitionSection title="Input Schema"><pre>{JSON.stringify(Object.fromEntries(capability.definition.inputs.map((input) => [input.name, `${input.value_type.toLowerCase()}${input.sensitive ? " (sensitive)" : ""}`])), null, 2)}</pre></DefinitionSection>
      <DefinitionSection title="Output Schema"><pre>{JSON.stringify(Object.fromEntries(capability.definition.outputs.map((output) => [output.name, output.value_type.toLowerCase()])), null, 2)}</pre></DefinitionSection>
      <DefinitionSection title="Execution Steps"><ol className="step-list">{capability.definition.steps.map((step) => <li key={step.step_id}><strong>{humanize(step.step_id)}</strong><small>{step.action.kind} · {step.action.target.value}{step.retry_policy ? ` · retry ${step.retry_policy.max_attempts}x` : ""}</small></li>)}</ol></DefinitionSection>
      <DefinitionSection title="Known Outcomes"><ul className="outcome-list">{capability.definition.business_outcomes.map((outcome) => <li key={outcome.code}><strong>{humanize(outcome.code)}</strong><span>{outcome.description}</span></li>)}</ul></DefinitionSection>
    </aside>
  );
}

function DefinitionSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="definition-section"><h4>{title}</h4>{children}</section>;
}