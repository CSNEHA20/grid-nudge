"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  ReferenceLine,
} from "recharts";
import { X, Info } from "lucide-react";

interface FleetLoadChartModalProps {
  isOpen: boolean;
  onClose: () => void;
  timesteps: Array<{
    step: number;
    sim_time: string;
    hour: number;
    is_peak_window: boolean;
    feeder_capacity_mw: number;
    baseline_total_load_mw: number;
    gridnudge_total_load_mw: number;
    baseline_stress: number;
    gridnudge_stress: number;
  }>;
}

export function FleetLoadChartModal({
  isOpen,
  onClose,
  timesteps = [],
}: FleetLoadChartModalProps) {
  if (!isOpen) return null;

  // Format chart data with time label HH:MM
  const chartData = timesteps.map((t) => {
    const h = Math.floor(t.hour);
    const m = Math.round((t.hour - h) * 60);
    const timeLabel = `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
    return {
      time: timeLabel,
      hour: t.hour,
      baseline: Number(t.baseline_total_load_mw.toFixed(2)),
      gridnudge: Number(t.gridnudge_total_load_mw.toFixed(2)),
      capacity: t.feeder_capacity_mw || 12.0,
      baselineStress: (t.baseline_stress * 100).toFixed(0),
      gridnudgeStress: (t.gridnudge_stress * 100).toFixed(0),
    };
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-5xl rounded-3xl glass-panel p-6 sm:p-8 border border-slate-700/60 shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                Simulation · Delhi Substation Feeder 7
              </span>
              <span className="text-xs text-slate-400">
                Heatwave Stress Scenario (2,000 EVs)
              </span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              24-Hour Fleet Load & Peak Shifting Profile
            </h2>
            <p className="text-sm text-slate-300 mt-0.5">
              Comparison between uncontrolled baseline charging and GridNudge safety-gated uplift allocation.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="w-10 h-10 rounded-full bg-navy-900 border border-slate-700/60 hover:border-slate-500 flex items-center justify-center text-slate-400 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-6 mb-4 px-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-orange-500" />
            <span className="text-slate-300 font-medium">Uncontrolled Broadcast Baseline</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-nudge-gold" />
            <span className="text-slate-200 font-semibold">GridNudge Safe Staggered Load</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-6 h-0.5 border-t border-dashed border-red-400" />
            <span className="text-red-300">Feeder Capacity Limit (12.0 MW)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-3 rounded-sm bg-orange-500/15 border border-orange-500/30" />
            <span className="text-slate-400">Peak Window (18:00 – 22:00)</span>
          </div>
        </div>

        {/* Recharts Container */}
        <div className="w-full h-80 sm:h-96">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="baselineArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="gridnudgeArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#facc15" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#facc15" stopOpacity={0.0} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis unit=" MW" stroke="#64748b" tick={{ fontSize: 11 }} domain={[0, 16]} />

              {/* Shaded peak window */}
              <ReferenceArea
                x1="18:00"
                x2="22:00"
                stroke="rgba(249, 115, 22, 0.4)"
                strokeOpacity={0.4}
                fill="rgba(249, 115, 22, 0.12)"
              />

              {/* Feeder Capacity limit */}
              <ReferenceLine
                y={12.0}
                stroke="#f87171"
                strokeDasharray="4 4"
                label={{ value: "Capacity 12 MW", fill: "#f87171", fontSize: 11, position: "top" }}
              />

              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="p-3 rounded-xl bg-navy-950/95 border border-slate-700/80 shadow-xl text-xs space-y-1">
                        <div className="font-bold text-white mb-1">{label}</div>
                        <div className="text-orange-400 font-medium">
                          Baseline Load: {data.baseline} MW ({data.baselineStress}% capacity)
                        </div>
                        <div className="text-nudge-yellow font-bold">
                          GridNudge Load: {data.gridnudge} MW ({data.gridnudgeStress}% capacity)
                        </div>
                        <div className="text-slate-400">
                          Feeder Capacity: 12.0 MW
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />

              <Area
                type="monotone"
                dataKey="baseline"
                stroke="#f97316"
                strokeWidth={2.5}
                fill="url(#baselineArea)"
              />
              <Area
                type="monotone"
                dataKey="gridnudge"
                stroke="#facc15"
                strokeWidth={3}
                fill="url(#gridnudgeArea)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Footer note */}
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <Info className="w-4 h-4 text-slate-500" />
            <span>
              Peak is shaved by staggering EV charging across the overnight solar/wind window (22:30–05:30) while respecting travel safety.
            </span>
          </div>
          <span className="font-mono text-slate-500">Seed 42 · CRN Synchronized</span>
        </div>
      </div>
    </div>
  );
}
