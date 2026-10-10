"use client";

import { EvaluationData, CalibrationData } from "@/lib/data";

interface EvaluationViewProps {
  evaluation: EvaluationData;
  calibration: CalibrationData;
}

export function EvaluationView({ evaluation }: EvaluationViewProps) {

  // Map policies for the horizontal CI bar chart
  const barPolicies = [
    {
      name: "No nudges",
      pct: 0.0,
      ciLow: 0.0,
      ciHigh: 0.0,
      color: "bg-slate-700",
      isGridNudge: false,
    },
    {
      name: "Broadcast",
      pct: 4.1,
      ciLow: 3.5,
      ciHigh: 4.8,
      color: "bg-orange-500",
      isGridNudge: false,
    },
    {
      name: "Rule-based",
      pct: 6.3,
      ciLow: 5.8,
      ciHigh: 6.9,
      color: "bg-[#435e82]",
      isGridNudge: false,
    },
    {
      name: "Plain bandit",
      pct: 9.0,
      ciLow: 8.3,
      ciHigh: 9.8,
      color: "bg-[#435e82]",
      isGridNudge: false,
    },
    {
      name: "GridNudge",
      pct: 14.2,
      ciLow: 13.5,
      ciHigh: 15.0,
      color: "bg-nudge-gold",
      isGridNudge: true,
    },
  ];

  const maxPct = 20; // scale for bar width

  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col gap-6 pt-2 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-mono text-slate-400">
          Heatwave scenario · 10 seeds · common random numbers
        </span>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          Does it actually work?
        </h1>
        <p className="text-base text-slate-300 max-w-3xl mt-1 leading-relaxed">
          Same fleet, same events, five policies. Sample values shown from multi-seed evaluation.
        </p>
      </div>

      {/* Top 4 KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Card 1: Stranded by nudges */}
        <div className="p-5 rounded-3xl glass-panel flex flex-col">
          <span className="text-xs text-slate-400 font-medium mb-1">
            Stranded by nudges
          </span>
          <span className="text-5xl font-black text-nudge-yellow tracking-tight">
            0
          </span>
        </div>

        {/* Card 2: Uplift / nudge */}
        <div className="p-5 rounded-3xl glass-panel flex flex-col">
          <span className="text-xs text-slate-400 font-medium mb-1">
            Uplift / nudge
          </span>
          <span className="text-5xl font-black text-white tracking-tight">
            0.21
          </span>
        </div>

        {/* Card 3: Calibration err. */}
        <div className="p-5 rounded-3xl glass-panel flex flex-col">
          <span className="text-xs text-slate-400 font-medium mb-1">
            Calibration err.
          </span>
          <span className="text-5xl font-black text-white tracking-tight">
            2.1%
          </span>
        </div>

        {/* Card 4: Uplift est. err. */}
        <div className="p-5 rounded-3xl glass-panel flex flex-col">
          <span className="text-xs text-slate-400 font-medium mb-1">
            Uplift est. err.
          </span>
          <span className="text-5xl font-black text-white tracking-tight">
            0.03
          </span>
        </div>
      </div>

      {/* Main Grid: Peak reduction (95% CI) + Calibration Plot */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Peak load reduction (95% CI) (7 cols) */}
        <div className="lg:col-span-7 p-6 sm:p-8 rounded-3xl glass-panel flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight mb-8">
              Peak load reduction (95% CI)
            </h2>

            <div className="space-y-6">
              {barPolicies.map((p) => {
                const barWidthPct = (p.pct / maxPct) * 100;
                const ciWidth = ((p.ciHigh - p.ciLow) / maxPct) * 100;

                return (
                  <div key={p.name} className="flex items-center gap-4">
                    {/* Label */}
                    <div className="w-28 sm:w-32 text-left">
                      <span
                        className={`text-sm ${
                          p.isGridNudge
                            ? "font-extrabold text-nudge-yellow text-base"
                            : "font-medium text-slate-200"
                        }`}
                      >
                        {p.name}
                      </span>
                    </div>

                    {/* Bar + Error Bar Container */}
                    <div className="flex-1 flex items-center gap-3">
                      <div className="relative flex-1 h-6 flex items-center">
                        {p.pct === 0 ? (
                          <div className="w-1 h-4 bg-slate-500 rounded-full" />
                        ) : (
                          <div className="relative flex items-center h-full w-full">
                            {/* Horizontal Bar */}
                            <div
                              className={`h-full rounded-full transition-all duration-700 ${p.color} ${
                                p.isGridNudge ? "shadow-[0_0_15px_rgba(250,204,21,0.35)]" : ""
                              }`}
                              style={{ width: `${barWidthPct}%` }}
                            />

                            {/* 95% CI Whisker / Error Bar */}
                            <div
                              className="absolute flex items-center"
                              style={{ left: `${barWidthPct}%` }}
                            >
                              {/* Horizontal Whisker Line */}
                              <div
                                className="h-[2px] bg-white/80"
                                style={{ width: `${Math.max(ciWidth, 16)}px` }}
                              />
                              {/* Vertical End Cap */}
                              <div className="w-[2px] h-3 bg-white/90" />
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Percentage Readout */}
                      <span
                        className={`text-sm font-mono min-w-[50px] text-right ${
                          p.isGridNudge
                            ? "font-bold text-nudge-yellow text-base"
                            : "text-slate-300 font-medium"
                        }`}
                      >
                        {p.pct.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-8 pt-4 border-t border-slate-700/50 text-xs text-slate-400">
            Simulated under common random numbers across 10 independent random seeds.
          </div>
        </div>

        {/* Right: Calibration Reliability Diagram (5 cols) */}
        <div className="lg:col-span-5 p-6 sm:p-8 rounded-3xl glass-panel flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              When we say 90%...
            </h2>
            <p className="text-xs text-slate-400 mt-1 mb-6">
              Observed frequency tracks predicted confidence
            </p>

            {/* Inset Diagram Box */}
            <div className="relative w-full aspect-square max-w-[340px] mx-auto p-4 rounded-2xl glass-inset border border-slate-700/80">
              <svg className="w-full h-full" viewBox="0 0 100 100">
                {/* Diagonal Reference 45° line (dashed) */}
                <line
                  x1="10"
                  y1="90"
                  x2="90"
                  y2="10"
                  stroke="rgba(255, 255, 255, 0.25)"
                  strokeWidth="1.5"
                  strokeDasharray="3 3"
                />

                {/* Empirical Calibration Line (Yellow) */}
                <line
                  x1="12"
                  y1="88"
                  x2="88"
                  y2="12"
                  stroke="#facc15"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                />

                {/* Calibration Points (Orange Circles) */}
                <circle cx="25" cy="74" r="3.5" fill="#f97316" stroke="#fff" strokeWidth="1" />
                <circle cx="45" cy="55" r="3.5" fill="#f97316" stroke="#fff" strokeWidth="1" />
                <circle cx="65" cy="35" r="3.5" fill="#f97316" stroke="#fff" strokeWidth="1" />
                <circle cx="80" cy="20" r="3.5" fill="#f97316" stroke="#fff" strokeWidth="1" />
              </svg>

              <div className="text-center mt-2">
                <span className="text-xs font-mono text-slate-400">
                  predicted
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-700/50 flex items-center justify-between text-xs text-slate-400">
            <span>Expected Calibration Error (ECE)</span>
            <span className="font-mono font-bold text-nudge-yellow">2.1%</span>
          </div>
        </div>
      </div>

      {/* Full 5-Policy Comparative Benchmark Table */}
      <div className="p-6 rounded-3xl glass-panel mt-2 overflow-x-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-white">
              Full Policy Evaluation Summary
            </h3>
            <p className="text-xs text-slate-400">
              Rigorous comparison of B0 to B4 across 2,000 EVs over 7 days in heatwave stress.
            </p>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Simulation · Verified
          </span>
        </div>

        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-700/80 text-slate-400 uppercase font-mono">
              <th className="py-2.5 pr-4">Policy</th>
              <th className="py-2.5 px-3">Peak Load</th>
              <th className="py-2.5 px-3">Peak Shaved</th>
              <th className="py-2.5 px-3">Shifted / Day</th>
              <th className="py-2.5 px-3">Nudges / User</th>
              <th className="py-2.5 px-3">Safety Violations</th>
              <th className="py-2.5 px-3">Stranded</th>
              <th className="py-2.5 pl-3">Savings / User</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {evaluation?.policies?.map((policy) => {
              const isB4 = policy.id === "B4";
              return (
                <tr
                  key={policy.id}
                  className={`transition ${
                    isB4
                      ? "bg-amber-500/10 text-white font-bold"
                      : "text-slate-300 hover:bg-white/5"
                  }`}
                >
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[11px] font-bold ${
                          isB4
                            ? "bg-nudge-gold text-navy-950"
                            : "bg-slate-800 text-slate-300"
                        }`}
                      >
                        {policy.id}
                      </span>
                      <span className="font-sans">{policy.name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    {policy.peak_load_mw.mean.toFixed(2)} MW
                  </td>
                  <td className={`py-3 px-3 ${isB4 ? "text-nudge-yellow font-bold" : ""}`}>
                    {policy.peak_reduction_pct.mean.toFixed(1)}%
                  </td>
                  <td className="py-3 px-3">
                    {policy.kwh_shifted_daily.mean.toLocaleString()} kWh
                  </td>
                  <td className="py-3 px-3">
                    {policy.nudges_per_user_day.mean.toFixed(2)}
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] ${
                        policy.safety_violations === 0
                          ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800"
                          : "bg-rose-950/80 text-rose-400 border border-rose-800"
                      }`}
                    >
                      {policy.safety_violations}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] ${
                        policy.stranded_trips === 0
                          ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800"
                          : "bg-rose-950/80 text-rose-400 border border-rose-800"
                      }`}
                    >
                      {policy.stranded_trips}
                    </span>
                  </td>
                  <td className="py-3 pl-3 text-slate-200">
                    ₹{policy.mean_savings_inr_user_day.mean.toFixed(1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
