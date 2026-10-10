/**
 * GridNudge TypeScript Contract Definitions
 * Generated from gridnudge.contracts.DecisionRecord
 * DO NOT EDIT DIRECTLY. Regenerate using python scripts/export_contracts.py
 */

export type PlanType = "default" | "delay" | "relocate" | "slow_charge" | "top_up_now";
export type Frame = "none" | "cost" | "green" | "battery" | "convenience" | "reassurance";
export type Timing = "at_plug_in" | "plus_30m" | "pre_peak";
export type CedarVerdict = "ALLOW" | "DENY" | "ERROR";
export type MessageSource = "llm" | "template" | "none";

export interface Journey {
  p_arrive_above_reserve: number;
  arrival_soc_q10: number;
  arrival_soc_q50: number;
  arrival_soc_q90: number;
  reserve_soc?: number;
}

export interface BatteryView {
  stress_score: number;
  soh_delta_range_pct: [number, number];
}

export interface StationView {
  eta_wait_min_q50: number;
  eta_wait_min_q90: number;
  reliability: number;
}

export interface GridView {
  stress_q50: number;
  stress_q90: number;
  green_window_start?: string | null;
  green_window_end?: string | null;
}

export interface Plan {
  plan_id: string;
  type: PlanType;
  start: string;
  kw: number;
  where: string;
  outcomes: Record<string, unknown>;
}

export interface Safety {
  invariants_ok: boolean;
  cedar: CedarVerdict;
  vetoed?: string[];
}

export interface Persuasion {
  chosen_plan?: string | null;
  frame: Frame;
  timing?: Timing | null;
  uplift_mean: number;
  uplift_p10: number;
  propensity: number;
  explored: boolean;
}

export interface Allocation {
  selected: boolean;
  shadow_price: number;
  slot?: string | null;
}

export interface Language {
  message?: string | null;
  facts_used?: Record<string, unknown>;
  verified?: boolean;
  source?: MessageSource;
}

export interface Outcome {
  adopted?: boolean | null;
  kwh_shifted?: number | null;
  opted_out?: boolean | null;
  reward?: number | null;
}

export interface DecisionRecord {
  decision_id: string;
  run_id: string;
  sim_time: string;
  user_id: string;
  ev: Record<string, unknown>;
  journey?: Journey | null;
  battery?: BatteryView | null;
  station?: StationView | null;
  grid?: GridView | null;
  plans?: Plan[];
  safety: Safety;
  persuasion: Persuasion;
  allocation: Allocation;
  language?: Language;
  outcome?: Outcome;
  fail_silent?: boolean;
  error?: string | null;
}
