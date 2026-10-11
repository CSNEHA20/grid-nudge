import fs from "fs/promises";
import path from "path";
import { DecisionRecord } from "@/types/decision-record";

export interface TimelineData {
  scenario: string;
  provenance: string;
  feeder_name: string;
  n_users?: number;
  timesteps: Array<{
    step: number;
    sim_time: string;
    hour: number;
    is_peak_window: boolean;
    is_heatwave: boolean;
    feeder_capacity_mw: number;
    base_load_mw: number;
    solar_gen_mw: number;
    baseline_ev_load_mw: number;
    gridnudge_ev_load_mw: number;
    baseline_total_load_mw: number;
    gridnudge_total_load_mw: number;
    baseline_stress: number;
    gridnudge_stress: number;
    nudges_delivered: number;
    safety_vetoes: number;
    learned_silence_count: number;
    shadow_price_inr: number;
  }>;
  summary?: Record<string, string | number | boolean | null>;
}

export interface EvaluationPolicy {
  id: string;
  name: string;
  description: string;
  peak_load_mw: { mean: number; ci_low: number; ci_high: number };
  peak_reduction_pct: { mean: number; ci_low: number; ci_high: number };
  kwh_shifted_daily: { mean: number; ci_low: number; ci_high: number };
  nudges_per_user_day: { mean: number; ci_low: number; ci_high: number };
  safety_violations: number;
  stranded_trips: number;
  mean_savings_inr_user_day: { mean: number; ci_low: number; ci_high: number };
  opt_out_rate_pct: { mean: number; ci_low: number; ci_high: number };
}

export interface EvaluationData {
  provenance: string;
  n_seeds: number;
  n_users: number;
  simulation_days: number;
  scenario: string;
  policies: EvaluationPolicy[];
}

export interface CalibrationData {
  metric: string;
  provenance: string;
  held_out_trips_count: number;
  expected_calibration_error: number;
  max_calibration_error: number;
  bins: Array<{
    bin_start: number;
    bin_end: number;
    mean_predicted: number;
    observed_freq: number;
    count: number;
  }>;
}

export interface DecisionIndexItem {
  decision_id: string;
  sim_time: string;
  user_id: string;
  status: "SENT" | "SILENT" | "VETOED" | "FAIL-SILENT";
  plan_type: string;
  frame: string;
  journey_conf_lb: number;
  uplift_mean: number;
  propensity: number;
  slot: string | null;
  outcome: string;
  kwh_shifted: number;
  station_id: number | null;
}

export interface StationData {
  id: number;
  name: string;
  location: string;
  lat: number;
  lon: number;
  charger_type: string;
  kw: number;
  connectors: number;
  active_connectors: number;
  queue_length: number;
  predicted_wait_min_q50: number;
  predicted_wait_min_q90: number;
  reliability: number;
  is_offline: boolean;
}

export interface TwinSnapshotData {
  provenance: string;
  sim_time: string;
  fleet: {
    total_evs: number;
    plugged_now: number;
    charging_now: number;
    waiting_queue: number;
    driving_now: number;
    parked_done: number;
    flexible_evs: number;
    inflexible_evs: number;
    cohort_hourly: Array<{
      hour: string;
      plugged: number;
      charging: number;
      driving: number;
    }>;
  };
  grid: {
    feeder_zone: string;
    feeder_capacity_mw: number;
    current_load_mw: number;
    baseline_uncontrolled_mw: number;
    solar_share_pct: number;
    current_tariff_slot: string;
    peak_price_inr_kwh: number;
    offpeak_price_inr_kwh: number;
    grid_stress_window: string;
    green_charging_window: string;
    forecast: {
      seasonal_naive_peak_mw: number;
      chronos_probabilistic_peak_mw: { q10: number; q50: number; q90: number };
    };
  };
  battery: {
    stress_histogram: Array<{ bucket: string; count: number; pct: number }>;
    mean_fleet_stress: number;
    soh_delta_simulated_range: {
      min_pct: number;
      max_pct: number;
      caption: string;
    };
  };
}

export interface FlexibilityData {
  provenance: string;
  horizon_hours: number;
  peak_window_hours: string;
  timesteps: Array<{
    hour: number;
    label: string;
    physical_envelope_kw: { p10: number; p50: number; p90: number };
    adoption_weighted_kw: { p10: number; p50: number; p90: number };
  }>;
}

export interface EventItem {
  type: string;
  name: string;
  status: string;
  start_sim_time: string;
  duration_hours: number;
  params: Record<string, string | number | boolean | number[]>;
  description: string;
}

export interface AssumptionItem {
  category: string;
  parameter: string;
  assumed_value: string;
  rationale: string;
  grounding_method: string;
}

export interface SourceItem {
  name: string;
  tier: string;
  category: string;
  description: string;
  license_access: string;
  usage_in_gridnudge: string;
}

export interface PolicyRuleItem {
  id: string;
  name: string;
  plain_language: string;
  cedar_statement: string;
  category: string;
}

export interface TestDriveProfile {
  id: string;
  profile_name: string;
  inputs: {
    daily_commute_km: number;
    weekend_trip_km: number;
    home_charging_access: boolean;
    climate_zone: string;
    current_monthly_fuel_inr: number;
    offpeak_tariff_inr: number;
  };
  outputs: {
    ownership_confidence_pct: number;
    suitability_verdict: "STRONG_FIT" | "BORDERLINE" | "NOT_RECOMMENDED";
    verdict_title: string;
    summary_reasons: string[];
    monthly_ev_energy_cost_inr: number;
    monthly_fuel_savings_inr: number;
    annual_savings_inr: number;
    public_charging_dependency_pct: number;
    battery_stress_rating: string;
    weeks_at_risk_out_of_52: number;
    weekly_risk_timeline: string[];
  };
}

export interface CopilotData {
  provenance: string;
  suggested_questions: string[];
  conversations: Array<{
    question: string;
    answer: string;
    citations: Array<{ type: string; id: string; label: string }>;
    tools_used: string[];
    scenario_preview?: {
      title: string;
      events: Array<Record<string, string | number | boolean>>;
      projected_impact: string;
    };
  }>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE;
const DATA_MODE = process.env.NEXT_PUBLIC_DATA_MODE || (API_BASE ? "live" : "replay");

async function readJsonFile<T>(relativePath: string): Promise<T> {
  const fullPath = path.join(process.cwd(), relativePath);
  const content = await fs.readFile(fullPath, "utf-8");
  return JSON.parse(content) as T;
}

async function fetchFromApiOrFallback<T>(endpoint: string, fallbackFile: string): Promise<T> {
  if (DATA_MODE === "live" && API_BASE) {
    try {
      const res = await fetch(`${API_BASE.replace(/\/+$/, "")}${endpoint}`, { cache: "no-store" });
      if (res.ok) {
        return (await res.json()) as T;
      }
    } catch {
      // Graceful fallback to stored run file
    }
  }
  return await readJsonFile<T>(fallbackFile);
}

export async function getTimelineData(): Promise<TimelineData> {
  if (DATA_MODE === "live" && API_BASE) {
    try {
      const res = await fetch(`${API_BASE.replace(/\/+$/, "")}/metrics`, { cache: "no-store" });
      if (res.ok) {
        return (await res.json()) as TimelineData;
      }
    } catch {
      // Fallback
    }
  }
  try {
    return await readJsonFile<TimelineData>("public/replay/timeline.json");
  } catch {
    return await readJsonFile<TimelineData>("public/fixtures/metrics.timeline.json");
  }
}

export async function getDecisions(): Promise<DecisionRecord[]> {
  return await fetchFromApiOrFallback<DecisionRecord[]>("/decisions", "public/fixtures/decisions.sample.json");
}

export async function getDecisionById(id: string): Promise<DecisionRecord | null> {
  if (DATA_MODE === "live" && API_BASE) {
    try {
      const res = await fetch(`${API_BASE.replace(/\/+$/, "")}/decision/${id}`, { cache: "no-store" });
      if (res.ok) {
        return (await res.json()) as DecisionRecord;
      }
    } catch {
      // Fallback to local
    }
  }
  const decisions = await getDecisions();
  return decisions.find((d) => d.decision_id === id) || null;
}

export async function getDecisionsIndex(): Promise<DecisionIndexItem[]> {
  return await fetchFromApiOrFallback<DecisionIndexItem[]>("/decisions/index", "public/fixtures/decisions.index.json");
}

export async function getEvaluationData(): Promise<EvaluationData> {
  return await fetchFromApiOrFallback<EvaluationData>("/evaluation", "public/fixtures/evaluation.summary.json");
}

export async function getCalibrationData(): Promise<CalibrationData> {
  return await readJsonFile<CalibrationData>("public/fixtures/calibration.json");
}

export async function getFlexibilityData(): Promise<FlexibilityData> {
  return await readJsonFile<FlexibilityData>("public/fixtures/flexibility.json");
}

export async function getTwinSnapshot(): Promise<TwinSnapshotData> {
  return await readJsonFile<TwinSnapshotData>("public/fixtures/twin.snapshot.json");
}

export async function getStations(): Promise<StationData[]> {
  return await readJsonFile<StationData[]>("public/fixtures/stations.json");
}

export async function getEvents(): Promise<EventItem[]> {
  return await readJsonFile<EventItem[]>("public/fixtures/events.json");
}

export async function getAssumptions(): Promise<AssumptionItem[]> {
  return await readJsonFile<AssumptionItem[]>("public/fixtures/assumptions.json");
}

export async function getSources(): Promise<SourceItem[]> {
  return await readJsonFile<SourceItem[]>("public/fixtures/sources.json");
}

export async function getPolicies(): Promise<PolicyRuleItem[]> {
  return await readJsonFile<PolicyRuleItem[]>("public/fixtures/policies.json");
}

export async function getTestDriveProfiles(): Promise<{ samples: TestDriveProfile[] }> {
  return await readJsonFile<{ samples: TestDriveProfile[] }>("public/fixtures/testdrive.samples.json");
}

export async function getCopilotData(): Promise<CopilotData> {
  return await readJsonFile<CopilotData>("public/fixtures/copilot.samples.json");
}
