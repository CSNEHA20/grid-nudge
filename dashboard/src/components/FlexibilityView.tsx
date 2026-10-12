"use client";

import { useState } from "react";
import { Sliders } from "lucide-react";
import { FlexibilityData } from "@/lib/data";

interface FlexibilityViewProps {
  flexibilityData: FlexibilityData;
}

export function FlexibilityView({ flexibilityData }: FlexibilityViewProps) {
  const [budgetSlider, setBudgetSlider] = useState<number>(8); // 8% default budget
  const [viewMode, setViewMode] = useState<"side_by_side" | "envelope" | "adoption">("side_by_side");

  const timesteps = flexibilityData?.timesteps || [];

  // Budget slider precomputed multipliers (4% to 16%)
  // Base headline is 4.2 MW at 8%
  const budgetScale = budgetSlider / 8;
  const shiftableMw = (4.2 * Math.pow(budgetScale, 0.65)).toFixed(1);
  const uncertaintyMw = (0.6 * Math.sqrt(budgetScale)).toFixed(1);
  const nudgesPerUserDay = (0.24 * budgetScale).toFixed(2);

  // Peak timesteps: hours 17 to 23
  const peakTimesteps = timesteps.filter((t) => t.hour >= 17 && t.hour <= 23);

  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col gap-6 pt-2 pb-16">
      {/* Header */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono text-slate-400">
            Delhi Suburban Feeder · 24h Flexibility Horizon
          </span>
          <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            SIMULATION-BASED ESTIMATE
          </span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          Flexibility Forecast
        </h1>
        <p className="text-base text-slate-300 max-w-3xl leading-relaxed">
          Forecast of available flexible power across the plugged-in EV fleet during peak hours.
          Decomposes the theoretical physical envelope from the real behavioral adoption-weighted shift.
        </p>
      </div>

      {/* Module F1: Hero Headline Band Card */}
      <div className="p-6 sm:p-8 rounded-3xl glass-panel flex flex-wrap items-center justify-between gap-6 border-l-4 border-l-amber-500">
        <div>
          <span className="text-sm font-semibold text-slate-400 uppercase tracking-wider block">
            Expected Shiftable Power in Next Peak Window (18:00 – 22:30 IST)
          </span>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="text-5xl sm:text-6xl font-black text-amber-400 tracking-tight font-mono">
              {shiftableMw} MW
            </span>
            <span className="text-xl sm:text-2xl font-bold text-slate-300 font-mono">
              &plusmn; {uncertaintyMw} MW
            </span>
          </div>
          <p className="text-sm text-slate-300 mt-2">
            Monte Carlo 10th to 90th percentile credible interval across 2,000 EVs.
          </p>
        </div>

        {/* Module F4: What-If Attention Budget Slider */}
        <div className="p-5 rounded-2xl bg-black/30 border border-white/10 w-full md:w-80 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-300 font-semibold flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-amber-400" />
              What-If Attention Budget:
            </span>
            <span className="font-mono text-amber-400 font-bold text-base">
              {budgetSlider}% of EVs
            </span>
          </div>

          <input
            type="range"
            min={4}
            max={16}
            step={2}
            value={budgetSlider}
            onChange={(e) => setBudgetSlider(Number(e.target.value))}
            className="w-full accent-amber-400 cursor-pointer"
          />

          <div className="flex justify-between text-xs font-mono text-slate-400">
            <span>4% (Conservative)</span>
            <span>8% (Default)</span>
            <span>16% (Aggressive)</span>
          </div>

          <div className="pt-2 border-t border-white/5 flex justify-between text-sm font-mono text-slate-300">
            <span>Projected Nudges/User:</span>
            <span className="text-amber-300 font-bold">{nudgesPerUserDay}/day</span>
          </div>
        </div>
      </div>

      {/* Module F2: Decomposition: Physical Envelope vs Adoption-Weighted */}
      <div className="p-6 sm:p-8 rounded-3xl glass-panel space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Flexibility Decomposition: Physical Envelope vs. Behavioral Adoption
            </h2>
            <p className="text-sm text-slate-300 mt-1">
              Physical envelope represents theoretical capability without breaking driver trip deadlines.
              Adoption-weighted reflects the contextual bandit&apos;s expected user compliance.
            </p>
          </div>

          <div className="flex items-center gap-1 bg-navy-900 p-1 rounded-full border border-white/10 text-sm">
            <button
              type="button"
              onClick={() => setViewMode("side_by_side")}
              className={`px-3 py-1.5 rounded-full font-medium transition ${
                viewMode === "side_by_side"
                  ? "bg-amber-500 text-navy-950 font-bold"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Side-by-Side
            </button>
            <button
              type="button"
              onClick={() => setViewMode("adoption")}
              className={`px-3 py-1.5 rounded-full font-medium transition ${
                viewMode === "adoption"
                  ? "bg-amber-500 text-navy-950 font-bold"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Adoption Only
            </button>
          </div>
        </div>

        {/* Peak Hours Hourly Chart Grid */}
        <div className="space-y-4">
          <span className="text-sm uppercase font-mono text-slate-400 block">
            Hourly Peak Period Capacity (17:00 to 23:00 IST):
          </span>

          <div className="space-y-3">
            {peakTimesteps.map((t) => {
              const envKw = t.physical_envelope_kw.p50;
              const adoptKw = t.adoption_weighted_kw.p50 * budgetScale;
              const maxScaleKw = 2500;

              return (
                <div key={t.hour} className="space-y-1 text-sm font-mono">
                  <div className="flex justify-between text-slate-300">
                    <span className="font-bold text-white">{t.label} IST</span>
                    <div className="flex gap-4">
                      {viewMode === "side_by_side" && (
                        <span className="text-slate-400">
                          Physical: {(envKw / 1000).toFixed(2)} MW
                        </span>
                      )}
                      <span className="text-amber-400 font-bold">
                        Adoption: {(adoptKw / 1000).toFixed(2)} MW
                      </span>
                    </div>
                  </div>

                  <div className="h-5 rounded-full bg-slate-800/80 overflow-hidden flex relative">
                    {/* Physical Envelope Bar */}
                    {viewMode === "side_by_side" && (
                      <div
                        className="bg-slate-600/60 h-full rounded-full transition-all duration-500"
                        style={{ width: `${(envKw / maxScaleKw) * 100}%` }}
                        title={`Physical Envelope: ${envKw} kW`}
                      />
                    )}

                    {/* Adoption-Weighted Bar */}
                    <div
                      className="absolute left-0 top-0 bottom-0 bg-amber-400 h-full rounded-full transition-all duration-500 shadow-sm"
                      style={{ width: `${(adoptKw / maxScaleKw) * 100}%` }}
                      title={`Adoption-Weighted: ${adoptKw.toFixed(0)} kW`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="pt-4 border-t border-slate-700/50 flex flex-wrap items-center justify-between gap-2 text-sm text-slate-400">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-slate-600 inline-block" />
              Physical Envelope (Hard Constraints)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-amber-400 inline-block" />
              Adoption-Weighted (Bandit Expected Yield)
            </span>
          </div>
          <span className="font-mono text-slate-300">
            Feeder Relief Potential: 35.0% of peak load
          </span>
        </div>
      </div>
    </div>
  );
}
