"use client";

import { useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { TestDriveProfile } from "@/lib/data";

interface TestDriveViewProps {
  samples: TestDriveProfile[];
}

export function TestDriveView({ samples = [] }: TestDriveViewProps) {
  const [selectedProfileId, setSelectedProfileId] = useState<string>("good_fit");

  // Form interactive state initialised from selected sample
  const currentProfile =
    samples.find((s) => s.id === selectedProfileId) || samples[0];

  const [commuteKm, setCommuteKm] = useState<number>(
    currentProfile?.inputs?.daily_commute_km || 35
  );
  const [hasHomeCharging, setHasHomeCharging] = useState<boolean>(
    currentProfile?.inputs?.home_charging_access ?? true
  );
  const [fuelCost, setFuelCost] = useState<number>(
    currentProfile?.inputs?.current_monthly_fuel_inr || 8500
  );

  const handleSelectSample = (sample: TestDriveProfile) => {
    setSelectedProfileId(sample.id);
    setCommuteKm(sample.inputs.daily_commute_km);
    setHasHomeCharging(sample.inputs.home_charging_access);
    setFuelCost(sample.inputs.current_monthly_fuel_inr);
  };

  const outputs = currentProfile?.outputs || {
    ownership_confidence_pct: 96,
    suitability_verdict: "STRONG_FIT",
    verdict_title: "An EV is an excellent fit for your daily routine",
    summary_reasons: [],
    monthly_ev_energy_cost_inr: 2380,
    monthly_fuel_savings_inr: 6120,
    annual_savings_inr: 73440,
    public_charging_dependency_pct: 8,
    battery_stress_rating: "Low (0.16 / 1.0)",
    weeks_at_risk_out_of_52: 2,
    weekly_risk_timeline: [],
  };

  const isBorderline = outputs.suitability_verdict === "BORDERLINE";
  const isNotRecommended = outputs.suitability_verdict === "NOT_RECOMMENDED";

  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col gap-6 pt-2 pb-16">
      {/* Header */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono text-slate-400">
            Ownership Confidence · Pre-Purchase Decision Support
          </span>
          <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            HONEST SIMULATOR
          </span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          EV Test Drive: Ownership Confidence
        </h1>
        <p className="text-base text-slate-300 max-w-3xl leading-relaxed">
          Simulate a full year of ownership across Delhi NCR seasons before buying an EV.
          Honest evaluation: if an EV doesn&apos;t fit your charging access or commute, we tell you directly.
        </p>
      </div>

      {/* Preset Archetypes Picker */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 rounded-full bg-navy-800/90 border border-slate-700/60 max-w-fit">
        <span className="text-sm font-semibold text-slate-400 px-3">
          Load Sample Profile:
        </span>
        {samples.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => handleSelectSample(s)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition ${
              selectedProfileId === s.id
                ? s.id === "not_suitable"
                  ? "bg-rose-500 text-white font-bold shadow-md"
                  : s.id === "borderline"
                  ? "bg-amber-500 text-navy-950 font-bold shadow-md"
                  : "bg-emerald-500 text-navy-950 font-bold shadow-md"
                : "text-slate-300 hover:text-white hover:bg-white/5"
            }`}
          >
            {s.profile_name}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Input Form Card (4 cols) */}
        <div className="lg:col-span-4 p-6 rounded-3xl glass-panel space-y-5">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">
              Driving & Charging Profile
            </h2>
            <p className="text-sm text-slate-400 mt-0.5">
              Adjust commute and home wallbox access.
            </p>
          </div>

          <div className="space-y-4 text-sm font-medium text-slate-300">
            <div>
              <label className="block text-slate-400 mb-1">
                Daily Commute Distance: <strong className="text-white">{commuteKm} km/day</strong>
              </label>
              <input
                type="range"
                min={15}
                max={220}
                step={5}
                value={commuteKm}
                onChange={(e) => setCommuteKm(Number(e.target.value))}
                className="w-full accent-amber-400 cursor-pointer"
              />
              <div className="flex justify-between text-xs text-slate-400 font-mono mt-0.5">
                <span>15 km</span>
                <span>100 km</span>
                <span>220 km</span>
              </div>
            </div>

            <div className="pt-2 border-t border-white/5">
              <label className="block text-slate-400 mb-2">Dedicated Home Wallbox Access:</label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setHasHomeCharging(true)}
                  className={`flex-1 py-2 rounded-xl border text-sm font-semibold transition ${
                    hasHomeCharging
                      ? "bg-emerald-500/20 border-emerald-400 text-emerald-300"
                      : "bg-navy-900 border-white/10 text-slate-400"
                  }`}
                >
                  Yes (Dedicated)
                </button>
                <button
                  type="button"
                  onClick={() => setHasHomeCharging(false)}
                  className={`flex-1 py-2 rounded-xl border text-sm font-semibold transition ${
                    !hasHomeCharging
                      ? "bg-rose-500/20 border-rose-400 text-rose-300"
                      : "bg-navy-900 border-white/10 text-slate-400"
                  }`}
                >
                  No (Public Only)
                </button>
              </div>
            </div>

            <div className="pt-2 border-t border-white/5">
              <label className="block text-slate-400 mb-1">
                Current Monthly Petrol/Diesel Spend:
              </label>
              <div className="p-2.5 rounded-xl bg-navy-900 border border-white/10 text-white font-mono text-base">
                ₹{fuelCost.toLocaleString()} / month
              </div>
            </div>

            <div className="pt-2 border-t border-white/5 space-y-1 text-sm text-slate-400">
              <p>Climate Zone: Delhi NCR (Hot Summers / Dense Fog Winters)</p>
              <p>Off-Peak Tariff: ₹4.50 / kWh · Peak Tariff: ₹9.80 / kWh</p>
            </div>
          </div>
        </div>

        {/* Right: Results & Honest Negative Verdict (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {/* Verdict Banner Card */}
          <div
            className={`p-6 sm:p-8 rounded-3xl border transition shadow-xl ${
              isNotRecommended
                ? "bg-rose-950/40 border-rose-500/60 shadow-rose-500/10"
                : isBorderline
                ? "bg-amber-950/40 border-amber-500/60 shadow-amber-500/10"
                : "bg-emerald-950/40 border-emerald-500/60 shadow-emerald-500/10"
            }`}
          >
            <div className="flex flex-wrap items-baseline justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  {isNotRecommended ? (
                    <XCircle className="w-6 h-6 text-rose-400" />
                  ) : isBorderline ? (
                    <AlertTriangle className="w-6 h-6 text-amber-400" />
                  ) : (
                    <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                  )}
                  <span
                    className={`text-sm font-bold font-mono uppercase tracking-wider ${
                      isNotRecommended
                        ? "text-rose-400"
                        : isBorderline
                        ? "text-amber-400"
                        : "text-emerald-400"
                    }`}
                  >
                    Suitability Verdict: {outputs.suitability_verdict}
                  </span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {outputs.verdict_title}
                </h2>
              </div>

              {/* Confidence Readout */}
              <div className="text-right">
                <span
                  className={`text-5xl sm:text-6xl font-black font-mono tracking-tight ${
                    isNotRecommended
                      ? "text-rose-400"
                      : isBorderline
                      ? "text-amber-400"
                      : "text-emerald-400"
                  }`}
                >
                  {outputs.ownership_confidence_pct}%
                </span>
                <span className="text-sm text-slate-400 block font-mono">
                  Ownership Confidence
                </span>
              </div>
            </div>

            {/* Honest Reasons List */}
            <div className="mt-5 space-y-2 text-sm text-slate-200">
              <span className="font-semibold text-slate-400 block uppercase text-xs tracking-wider">
                Simulation Findings:
              </span>
              {outputs.summary_reasons.map((r, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-amber-400 font-bold">&bull;</span>
                  <span className="leading-relaxed">{r}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 52-Week Simulated Risk Timeline */}
          <div className="p-6 rounded-3xl glass-panel space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">
                  52-Week Annual Risk Timeline
                </h3>
                <p className="text-sm text-slate-400">
                  Simulated year tracking seasonal heatwaves, winter battery drop, and station queues.
                </p>
              </div>
              <span className="text-sm font-mono text-slate-300">
                {outputs.weeks_at_risk_out_of_52} weeks with elevated range risk
              </span>
            </div>

            {/* 52 Blocks Grid */}
            <div className="grid grid-cols-13 sm:grid-cols-26 gap-1.5 p-3 rounded-2xl bg-black/30 border border-white/5">
              {outputs.weekly_risk_timeline.map((risk, idx) => (
                <div
                  key={idx}
                  title={`Week ${idx + 1}: ${risk.replace("_", " ")}`}
                  className={`h-6 rounded-md transition hover:scale-110 cursor-pointer ${
                    risk === "safe"
                      ? "bg-emerald-500/80 hover:bg-emerald-400"
                      : risk === "mild_risk"
                      ? "bg-amber-400 hover:bg-yellow-300"
                      : "bg-rose-500 hover:bg-rose-400 animate-pulse"
                  }`}
                />
              ))}
            </div>

            <div className="flex items-center gap-4 text-sm font-mono text-slate-400 pt-1">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-emerald-500" /> Safe Week
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-amber-400" /> Mild Queue Risk
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-rose-500" /> Range/Stranding Risk
              </span>
            </div>
          </div>

          {/* Financial & Battery Profile Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-2xl glass-panel flex flex-col justify-between">
              <span className="text-sm text-slate-400 font-medium">Monthly EV Energy Cost</span>
              <span className="text-2xl font-black text-white font-mono mt-1">
                ₹{outputs.monthly_ev_energy_cost_inr.toLocaleString()}
              </span>
              <span className="text-xs text-emerald-400 mt-1">
                Saves ₹{outputs.monthly_fuel_savings_inr.toLocaleString()}/mo vs current
              </span>
            </div>

            <div className="p-4 rounded-2xl glass-panel flex flex-col justify-between">
              <span className="text-sm text-slate-400 font-medium">Public Charger Dependency</span>
              <span className="text-2xl font-black text-amber-300 font-mono mt-1">
                {outputs.public_charging_dependency_pct}%
              </span>
              <span className="text-xs text-slate-400 mt-1">
                {hasHomeCharging ? "Mostly overnight home charging" : "100% public DC reliant"}
              </span>
            </div>

            <div className="p-4 rounded-2xl glass-panel flex flex-col justify-between">
              <span className="text-sm text-slate-400 font-medium">Battery Stress Rating</span>
              <span className="text-2xl font-black text-white font-mono mt-1">
                {outputs.battery_stress_rating}
              </span>
              <span className="text-xs text-slate-400 mt-1">
                Cell thermal & DoD stress
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Mandatory Honest Disclaimer (§5.8) */}
      <div className="p-4 rounded-2xl bg-black/40 border border-white/10 text-sm text-slate-400 leading-relaxed text-center font-mono">
        Disclaimer: This EV Test Drive provides decision support simulated under stated vehicle and charging network assumptions. It is not financial advice, range guarantee, or warranty.
      </div>
    </div>
  );
}
