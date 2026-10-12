"use client";

import { useState } from "react";
import {
  Car,
  Zap,
  Battery,
  MapPin,
  ChevronRight,
  X,
} from "lucide-react";
import { TwinSnapshotData, StationData } from "@/lib/data";

interface TwinViewProps {
  twinSnapshot: TwinSnapshotData;
  stations: StationData[];
}

export function TwinView({ twinSnapshot, stations }: TwinViewProps) {
  const [selectedStation, setSelectedStation] = useState<StationData | null>(null);
  const [forecastModel, setForecastModel] = useState<"chronos" | "seasonal_naive">("chronos");

  const fleet = twinSnapshot?.fleet || {
    total_evs: 2000,
    plugged_now: 412,
    charging_now: 184,
    waiting_queue: 12,
    driving_now: 620,
    parked_done: 772,
    flexible_evs: 298,
    inflexible_evs: 114,
    cohort_hourly: [],
  };

  const grid = twinSnapshot?.grid || {
    feeder_zone: "Zone 7 · Delhi Suburban",
    feeder_capacity_mw: 12.0,
    current_load_mw: 11.22,
    baseline_uncontrolled_mw: 15.17,
    solar_share_pct: 0.0,
    current_tariff_slot: "peak",
    peak_price_inr_kwh: 9.8,
    offpeak_price_inr_kwh: 4.5,
    grid_stress_window: "18:00 - 22:30",
    green_charging_window: "22:30 - 05:30",
    forecast: {
      seasonal_naive_peak_mw: 14.8,
      chronos_probabilistic_peak_mw: { q10: 13.9, "q50": 14.6, "q90": 15.3 },
    },
  };

  const battery = twinSnapshot?.battery || {
    stress_histogram: [],
    mean_fleet_stress: 0.23,
    soh_delta_simulated_range: {
      min_pct: -0.015,
      max_pct: 0.042,
      caption: "Relative difference under stated assumptions, not a lifespan prediction.",
    },
  };

  return (
    <div className="w-full max-w-7xl mx-auto flex flex-col gap-6 pt-2 pb-16">
      {/* Header */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono text-slate-400">
            Delhi Feeder Zone 7 · 2,000 EVs Environment
          </span>
          <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            DIGITAL TWIN · SIMULATION
          </span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          Digital Twin Explorer
        </h1>
        <p className="text-base text-slate-300 max-w-3xl leading-relaxed">
          Inspect the physical environment GridNudge operates within: fleet dynamics, public charging hubs,
          substation feeder load, and electrochemical battery stress distributions.
        </p>
      </div>

      {/* 4-Panel Grid: T1 Fleet, T2 Stations, T3 Grid, T4 Batteries */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* T1: Fleet Panel */}
        <div className="p-6 sm:p-8 rounded-3xl glass-panel flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <Car className="w-5 h-5 text-amber-400" />
                Fleet Physical Dynamics
              </div>
              <span className="text-sm font-mono px-2.5 py-0.5 rounded bg-white/5 text-amber-300 border border-white/10">
                2,000 EVs Total
              </span>
            </div>

            {/* Headline Plugged-in Now */}
            <div className="p-4 rounded-2xl bg-black/30 border border-white/5 flex items-baseline justify-between mb-5">
              <div>
                <span className="text-4xl sm:text-5xl font-black text-amber-400 font-mono">
                  {fleet.plugged_now}
                </span>
                <span className="text-sm text-slate-400 block mt-0.5">
                  EVs plugged-in right now (18:45 sim)
                </span>
              </div>
              <div className="text-right">
                <span className="text-sm font-bold text-emerald-400 block">
                  {fleet.flexible_evs} Flexible
                </span>
                <span className="text-sm text-slate-400 block">
                  {fleet.inflexible_evs} Inflexible (Deadline bound)
                </span>
              </div>
            </div>

            {/* Counts by status */}
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-2.5 text-center text-sm">
              <div className="p-2.5 rounded-xl bg-navy-900/60 border border-white/5">
                <span className="text-slate-400 block text-xs uppercase">Driving</span>
                <span className="text-base font-bold text-white font-mono">{fleet.driving_now}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-navy-900/60 border border-white/5">
                <span className="text-slate-400 block text-xs uppercase">Charging</span>
                <span className="text-base font-bold text-amber-300 font-mono">{fleet.charging_now}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-navy-900/60 border border-white/5">
                <span className="text-slate-400 block text-xs uppercase">Queueing</span>
                <span className="text-base font-bold text-rose-300 font-mono">{fleet.waiting_queue}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-navy-900/60 border border-white/5">
                <span className="text-slate-400 block text-xs uppercase">Plugged</span>
                <span className="text-base font-bold text-white font-mono">{fleet.plugged_now}</span>
              </div>
              <div className="p-2.5 rounded-xl bg-navy-900/60 border border-white/5">
                <span className="text-slate-400 block text-xs uppercase">Done/Parked</span>
                <span className="text-base font-bold text-slate-300 font-mono">{fleet.parked_done}</span>
              </div>
            </div>

            {/* Cohort hourly snapshot */}
            <div className="mt-5 space-y-2">
              <span className="text-sm uppercase font-mono text-slate-400 block">
                Fleet Distribution by Time of Day:
              </span>
              <div className="space-y-1.5 text-sm font-mono">
                {fleet.cohort_hourly.map((c, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="w-12 text-slate-400">{c.hour}</span>
                    <div className="flex-1 h-3 rounded-full bg-slate-800 overflow-hidden flex">
                      <div
                        className="bg-amber-400 h-full"
                        style={{ width: `${(c.charging / fleet.total_evs) * 100 * 3}%` }}
                        title={`Charging: ${c.charging}`}
                      />
                      <div
                        className="bg-blue-400/80 h-full"
                        style={{ width: `${(c.driving / fleet.total_evs) * 100 * 2}%` }}
                        title={`Driving: ${c.driving}`}
                      />
                    </div>
                    <span className="text-slate-300 text-sm w-20 text-right">
                      {c.plugged} plugged
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-5 pt-3 border-t border-slate-700/50 text-sm text-slate-400">
            Physical envelope derived from departure deadlines and nominal charging power.
          </div>
        </div>

        {/* T2: Station Map and List */}
        <div className="p-6 sm:p-8 rounded-3xl glass-panel flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <MapPin className="w-5 h-5 text-cyan-400" />
                Delhi Public DC Fast Plazas ({stations.length})
              </div>
              <span className="text-sm font-mono px-2 py-0.5 rounded bg-white/5 text-slate-300">
                Ministry of Power (Dataful)
              </span>
            </div>

            <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {stations.map((st) => (
                <div
                  key={st.id}
                  onClick={() => setSelectedStation(st)}
                  className={`p-3.5 rounded-2xl border transition cursor-pointer flex items-center justify-between ${
                    selectedStation?.id === st.id
                      ? "bg-cyan-500/15 border-cyan-400/50 shadow-md"
                      : st.is_offline
                      ? "bg-rose-950/20 border-rose-500/30 opacity-70"
                      : "bg-navy-900/60 border-white/10 hover:border-white/20 hover:bg-white/5"
                  }`}
                >
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-white">
                        {st.name}
                      </span>
                      {st.is_offline ? (
                        <span className="px-1.5 py-0.2 rounded text-xs font-mono font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                          OFFLINE
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.2 rounded text-xs font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          ONLINE
                        </span>
                      )}
                    </div>
                    <span className="text-sm text-slate-400 mt-0.5">
                      {st.location} · {st.charger_type} ({st.kw} kW)
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-right">
                    <div className="flex flex-col font-mono text-sm">
                      <span className="text-white">
                        {st.active_connectors}/{st.connectors} busy
                      </span>
                      <span
                        className={
                          st.predicted_wait_min_q50 > 10
                            ? "text-rose-400 font-bold"
                            : "text-slate-400"
                        }
                      >
                        Wait: {st.predicted_wait_min_q50}m
                      </span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-700/50 flex items-center justify-between text-sm text-slate-400">
            <span>Station downtime simulated (MTBF 7d, MTTR 4h)</span>
            <span className="font-mono text-amber-300">OCPP Queue Telemetry</span>
          </div>
        </div>

        {/* T3: Grid Demand & Forecast */}
        <div className="p-6 sm:p-8 rounded-3xl glass-panel flex flex-col justify-between">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <Zap className="w-5 h-5 text-amber-400" />
                Feeder Zone 7 Demand & Forecast
              </div>

              {/* Forecast Model Toggle */}
              <div className="flex items-center gap-1 bg-navy-900 p-1 rounded-full border border-white/10 text-sm">
                <button
                  type="button"
                  onClick={() => setForecastModel("chronos")}
                  className={`px-2.5 py-1 rounded-full font-medium transition ${
                    forecastModel === "chronos"
                      ? "bg-amber-500 text-navy-950 font-bold"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Chronos Probabilistic
                </button>
                <button
                  type="button"
                  onClick={() => setForecastModel("seasonal_naive")}
                  className={`px-2.5 py-1 rounded-full font-medium transition ${
                    forecastModel === "seasonal_naive"
                      ? "bg-amber-500 text-navy-950 font-bold"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Seasonal-Naive
                </button>
              </div>
            </div>

            {/* Grid KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
              <div className="p-3 rounded-2xl bg-navy-900/60 border border-white/5">
                <span className="text-xs text-slate-400 uppercase block">Grid Stress Window</span>
                <span className="text-base font-bold text-orange-400 font-mono">
                  {grid.grid_stress_window}
                </span>
              </div>
              <div className="p-3 rounded-2xl bg-navy-900/60 border border-white/5">
                <span className="text-xs text-slate-400 uppercase block">Green Window</span>
                <span className="text-base font-bold text-emerald-400 font-mono">
                  {grid.green_charging_window}
                </span>
              </div>
              <div className="p-3 rounded-2xl bg-navy-900/60 border border-white/5">
                <span className="text-xs text-slate-400 uppercase block">ToU Tariff</span>
                <span className="text-base font-bold text-amber-300 font-mono">
                  ₹{grid.peak_price_inr_kwh} / ₹{grid.offpeak_price_inr_kwh} kWh
                </span>
              </div>
            </div>

            {/* Forecast Readout */}
            <div className="p-4 rounded-2xl bg-black/30 border border-white/5 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-300 font-semibold">
                  {forecastModel === "chronos"
                    ? "Chronos Zero-Shot Peak Forecast (18:00 - 22:00):"
                    : "Seasonal-Naive 7-Day Baseline Peak Forecast:"}
                </span>
                <span className="font-mono text-amber-400 font-bold text-base">
                  {forecastModel === "chronos"
                    ? `${grid.forecast?.chronos_probabilistic_peak_mw?.q50 || 14.6} MW (q10: ${grid.forecast?.chronos_probabilistic_peak_mw?.q10 || 13.9}, q90: ${grid.forecast?.chronos_probabilistic_peak_mw?.q90 || 15.3})`
                    : `${grid.forecast?.seasonal_naive_peak_mw || 14.8} MW`}
                </span>
              </div>
              <p className="text-sm text-slate-400">
                Feeder limit: 12.0 MW. Without GridNudge intervention, peak demand breaches
                safe line by +26% during evening heatwave hours.
              </p>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-700/50 text-sm text-slate-400">
            Duck curve baseline grounded in Delhi DISCOM hourly substation records.
          </div>
        </div>

        {/* T4: Battery Degradation & Stress */}
        <div className="p-6 sm:p-8 rounded-3xl glass-panel flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <Battery className="w-5 h-5 text-emerald-400" />
                Battery Stress Distribution (Fleet-Wide)
              </div>
              <span className="text-sm font-mono px-2 py-0.5 rounded bg-white/5 text-emerald-300">
                Mean Stress: {battery.mean_fleet_stress}
              </span>
            </div>

            {/* Histogram */}
            <div className="space-y-2.5">
              {battery.stress_histogram.map((b, i) => (
                <div key={i} className="flex items-center gap-3 text-sm font-mono">
                  <span className="w-36 text-slate-300 truncate">{b.bucket}</span>
                  <div className="flex-1 h-3 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full ${
                        i < 2
                          ? "bg-emerald-400"
                          : i === 2
                          ? "bg-amber-400"
                          : "bg-rose-400"
                      }`}
                      style={{ width: `${b.pct}%` }}
                    />
                  </div>
                  <span className="w-12 text-right text-slate-400">{b.pct}%</span>
                </div>
              ))}
            </div>

            {/* Simulated SoH Range Caption (§5.6) */}
            <div className="mt-6 p-4 rounded-2xl bg-navy-900/60 border border-white/5 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-300 font-semibold">Simulated SoH Delta Range:</span>
                <span className="font-mono text-emerald-300 font-bold">
                  [{battery.soh_delta_simulated_range.min_pct}%, +{battery.soh_delta_simulated_range.max_pct}%]
                </span>
              </div>
              <p className="text-sm text-slate-400 italic">
                &ldquo;{battery.soh_delta_simulated_range.caption}&rdquo;
              </p>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-700/50 text-sm text-slate-400">
            Semi-empirical cycle + calendar aging model from NASA PCoE & Oxford lab datasets.
          </div>
        </div>
      </div>

      {/* Station Detail Drawer Modal if clicked */}
      {selectedStation && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#1b2b3d] border border-cyan-400/40 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-cyan-400" />
                <h3 className="text-lg font-bold text-white">{selectedStation.name}</h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedStation(null)}
                className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white flex items-center justify-center transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-sm text-slate-300">
              <p>Location: {selectedStation.location}</p>
              <p>Type: {selectedStation.charger_type} ({selectedStation.kw} kW)</p>
              <p>
                Connectors: {selectedStation.active_connectors} active /{" "}
                {selectedStation.connectors} total
              </p>
              <p>Queue: {selectedStation.queue_length} vehicles waiting</p>
              <p>
                Estimated Wait at ETA: {selectedStation.predicted_wait_min_q50} min (q50) ·{" "}
                {selectedStation.predicted_wait_min_q90} min (q90)
              </p>
              <p>Assumed Hardware Reliability: {(selectedStation.reliability * 100).toFixed(0)}%</p>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedStation(null)}
                className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-navy-950 font-bold text-sm"
              >
                Close Station Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
