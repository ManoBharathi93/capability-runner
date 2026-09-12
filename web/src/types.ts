export type ApiErrorBody = { error: { code: string; summary: string } };

export type CapabilityInput = {
  name: string;
  value_type: string;
  required: boolean;
  sensitive: boolean;
};

export type CapabilityOutput = {
  name: string;
  value_type: string;
  source: { kind: string; parser: string; target: { value: string } };
};

export type CapabilityStep = {
  kind: "action";
  step_id: string;
  action: { kind: "fill" | "click"; target: { value: string } };
  precondition: unknown;
  postcondition: unknown;
  retry_policy: { kind: string; max_attempts: number; delay_ms: number } | null;
};

export type Capability = {
  capability_id: string;
  version: string;
  name: string;
  description: string;
  application: string;
  surface_kind: string;
  status: "READY";
  input_count: number;
  output_count: number;
  step_count: number;
  updated_at: string;
  definition: {
    inputs: CapabilityInput[];
    outputs: CapabilityOutput[];
    steps: CapabilityStep[];
    success_conditions: unknown[];
    business_outcomes: Array<{ code: string; description: string }>;
  };
};

export type RunSummary = {
  run_id: string;
  demo_kind: string;
  status: string;
  capability_id?: string;
  capability_version?: string;
  replay_result?: string | null;
  discovery_result?: string;
  business_outcome?: string | null;
  failure_reason?: string | null;
  outputs?: Record<string, string | number>;
  balance_minor_units?: number;
  currency?: string;
  provider?: string;
  browser_action_count?: number;
  discovery_model_calls?: number;
  builder_model_calls?: number;
  replay_model_calls?: number;
  event_count: number;
  created_at: string;
};

export type EvidenceEvent = {
  event_id: string;
  timestamp: string;
  event_type: string;
  component: string;
  run_id: string;
  session_id: string | null;
  step_id: string | null;
  action_id: string | null;
  outcome: string | null;
  reason_code: string | null;
  summary: string | null;
  metadata: Record<string, unknown>;
};

export type Intervention = {
  intervention_id: string | null;
  run_id: string;
  capability_id: string | null;
  reason_code: string;
  reason?: string;
  summary?: string;
  control_state: string;
  state_label: string;
  active: boolean;
  created_at?: string;
  blocked_action?: string;
  generation?: number;
  generation_before?: number;
  generation_after?: number;
  replay_result?: string;
};

export type OperatorControl = {
  semantic_target: string;
  label: string;
  action_kind: "fill" | "click";
  sensitive: boolean;
};

export type Overview = {
  capability_count: number;
  run_count: number;
  active_run_count: number;
  intervention_count: number;
  verified_run_count: number;
  system_health: "UNAVAILABLE";
  environment: "LOCAL_REVIEW";
  recent_runs: RunSummary[];
};