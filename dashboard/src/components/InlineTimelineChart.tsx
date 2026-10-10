"use client";

import { useMemo } from "react";
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

interface TimestepItem {
  step: number;
  sim_time: string;
  hour: number;
  is_peak_window: boolean;
  is_heatwave?: boolean;
  feeder_capacity_mw: number;
  base_load_mw?: number;
  solar_gen_mw?: number;
  baseline_total_load_mw: number;
  gridnudge_total_load_mw: number;
  baseline_stress: number;
  gridnudge_stress: number;
}

interface InlineTimelineChartProps {
  timesteps: TimestepItem[];
  currentStepIndex: number;
  onStepSelect?: (step: number) => void;
  activeEvent?: string;
}

export function InlineTimelineChart({
  timesteps = [],
  currentStepIndex,
  onStepSelect,
  activeEvent = "none",
}: InlineTimelineChartProps) {
  const chartData = useMemo(() => {
    return timesteps.map((t) => {
      const h = Math.floor(t.hour);
      const m = Math.round((t.hour - h) * 60);
      const timeLabel = `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
      const solarGen = t.solar_gen_mw || 0;
      // Solar share roughly relative to 3 MW max solar
      const solarPct = Math.min(Math.round((solarGen / 3.0) * 100), 100);

      // Tariff definition: 00-06 Off-peak (low), 06-18 Normal (mid), 18-22 Peak (peak), 22-24 Normal
      let tariff: "low" | "mid" | "peak" = "mid";
      if (t.hour >= 0 && t.hour < 6) tariff = "low";
      else if (t.hour >= 18 && t.hour < 22) tariff = "peak";

      return {
        step: t.step,
        time: timeLabel,
        hour: t.hour,
        baseline: Number(t.baseline_total_load_mw.toFixed(2)),
        gridnudge: Number(t.gridnudge_total_load_mw.toFixed(2)),
        capacity: t.feeder_capacity_mw || 12.0,
        solarPct,
        solarGen: Number(solarGen.toFixed(1)),
        tariff,
        isPeak: t.is_peak_window,
      };
    });
  }, [timesteps]);

  const currentPoint = chartData[currentStepIndex] || chartData[74];

  return (
    <div className="w-full flex flex-col items-center">
      {activeEvent !== "none" && (
        <div className="w-full flex justify-end px-3 mb-1">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-orange-500/15 text-orange-300 border border-orange-500/30 uppercase font-bold">
            Scenario Event: {activeEvent.replace("_", " ")}
          </span>
        </div>
      )}
      <div className="w-full h-[310px] sm:h-[340px] relative select-none">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 15, right: 10, left: -20, bottom: 0 }}
            onClick={(e) => {
              if (e && typeof e.activeTooltipIndex === "number" && onStepSelect) {
                onStepSelect(e.activeTooltipIndex);
              }
            }}
          >
            <defs>
              {/* Baseline gradient (orange) */}
              <linearGradient id="chartBaselineGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#f97316" stopOpacity={0.0} />
              </linearGradient>

              {/* GridNudge gradient (yellow) */}
              <linearGradient id="chartGridnudgeGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#facc15" stopOpacity={0.45} />
                <stop offset="95%" stopColor="#facc15" stopOpacity={0.0} />
              </linearGradient>

              {/* Solar share subtle area */}
              <linearGradient id="chartSolarGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255, 255, 255, 0.07)"
              vertical={false}
            />

            <XAxis
              dataKey="time"
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              interval={11} // ~ every 3 hours
            />

            <YAxis
              stroke="#64748b"
              fontSize={10}
              domain={[0, 16]}
              tickLine={false}
              unit=" MW"
            />

            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  const overshoot = data.baseline > data.capacity;
                  return (
                    <div className="p-3 rounded-xl bg-navy-950/95 border border-slate-700/80 backdrop-blur-md shadow-2xl text-xs space-y-1.5 z-40">
                      <div className="flex items-center justify-between gap-4 font-mono pb-1 border-b border-slate-800">
                        <span className="font-bold text-white">{data.time} IST</span>
                        <span
                          className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                            data.isPeak
                              ? "bg-red-500/20 text-red-300"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {data.isPeak ? "Peak Window" : "Standard Window"}
                        </span>
                      </div>

                      <div className="flex justify-between items-center text-orange-400">
                        <span>Broadcast Baseline:</span>
                        <span className="font-mono font-bold">
                          {data.baseline} MW{" "}
                          <span className="text-[10px]">
                            ({Math.round((data.baseline / data.capacity) * 100)}%)
                          </span>
                        </span>
                      </div>

                      <div className="flex justify-between items-center text-nudge-gold">
                        <span>GridNudge Safe:</span>
                        <span className="font-mono font-bold">
                          {data.gridnudge} MW{" "}
                          <span className="text-[10px]">
                            ({Math.round((data.gridnudge / data.capacity) * 100)}%)
                          </span>
                        </span>
                      </div>

                      <div className="flex justify-between items-center text-slate-400 text-[11px]">
                        <span>Feeder Capacity:</span>
                        <span className="font-mono">{data.capacity} MW</span>
                      </div>

                      <div className="flex justify-between items-center text-sky-300 text-[11px]">
                        <span>Solar Gen:</span>
                        <span className="font-mono">{data.solarGen} MW ({data.solarPct}%)</span>
                      </div>

                      <div className="flex justify-between items-center text-slate-300 text-[11px] pt-1 border-t border-slate-800/80">
                        <span>Tariff Slot:</span>
                        <span className="font-mono uppercase font-semibold text-amber-400">
                          {data.tariff}
                        </span>
                      </div>

                      {overshoot && (
                        <div className="text-[10px] text-red-400 font-semibold pt-0.5">
                          ⚠ Feeder Limit Violated (+{(data.baseline - data.capacity).toFixed(1)} MW)
                        </div>
                      )}
                    </div>
                  );
                }
                return null;
              }}
            />

            {/* Shaded Peak Window (18:00 - 22:00) */}
            <ReferenceArea
              x1="18:00"
              x2="22:00"
              fill="rgba(249, 115, 22, 0.12)"
              stroke="rgba(249, 115, 22, 0.3)"
              strokeDasharray="2 2"
              label={{
                value: "PEAK WINDOW (18:00–22:00)",
                position: "insideTop",
                fill: "#ea580c",
                fontSize: 10,
                fontWeight: 600,
              }}
            />

            {/* Capacity Threshold Line */}
            <ReferenceLine
              y={12.0}
              stroke="#ef4444"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              label={{
                value: "12.0 MW Feeder Capacity",
                position: "insideTopRight",
                fill: "#f87171",
                fontSize: 10,
              }}
            />

            {/* Solar Generation Area */}
            <Area
              type="monotone"
              dataKey="solarGen"
              stroke="#38bdf8"
              strokeWidth={1.2}
              fill="url(#chartSolarGrad)"
              dot={false}
              opacity={0.7}
            />

            {/* Uncontrolled Broadcast baseline curve */}
            <Area
              type="monotone"
              dataKey="baseline"
              stroke="#f97316"
              strokeWidth={2.2}
              fill="url(#chartBaselineGrad)"
              dot={false}
              activeDot={{ r: 5, fill: "#f97316", stroke: "#fff" }}
            />

            {/* GridNudge safe staggered load curve */}
            <Area
              type="monotone"
              dataKey="gridnudge"
              stroke="#facc15"
              strokeWidth={2.5}
              fill="url(#chartGridnudgeGrad)"
              dot={false}
              activeDot={{ r: 5, fill: "#facc15", stroke: "#fff" }}
            />

            {/* Current Sim Step Playhead indicator */}
            {currentPoint && (
              <ReferenceLine
                x={currentPoint.time}
                stroke="#ffffff"
                strokeWidth={2}
                label={{
                  value: currentPoint.time,
                  position: "top",
                  fill: "#ffffff",
                  fontSize: 10,
                  fontWeight: 700,
                }}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Tariff Strip Bar along the bottom per spec §5.1 L1 */}
      <div className="w-full mt-2 pt-2 border-t border-slate-800">
        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1 px-1">
          <span className="font-semibold uppercase tracking-wider text-slate-300">
            Tariff Bands (₹/kWh)
          </span>
          <span className="font-mono">Delhi EV Tariff Schedule</span>
        </div>

        <div className="w-full h-4 rounded-md overflow-hidden flex border border-slate-700/60 text-[9px] font-mono font-bold text-center leading-4 select-none">
          {/* 00:00 - 06:00: Off-Peak (25% of 24h) */}
          <div
            className="h-full bg-emerald-600/30 text-emerald-300 border-r border-emerald-500/20"
            style={{ width: "25%" }}
            title="Off-peak: ₹4.5/kWh (00:00–06:00)"
          >
            OFF-PEAK (₹4.5)
          </div>

          {/* 06:00 - 18:00: Standard Normal (50% of 24h) */}
          <div
            className="h-full bg-sky-600/25 text-sky-300 border-r border-sky-500/20"
            style={{ width: "50%" }}
            title="Normal: ₹7.0/kWh (06:00–18:00)"
          >
            NORMAL (₹7.0)
          </div>

          {/* 18:00 - 22:00: Critical Peak (16.7% of 24h) */}
          <div
            className="h-full bg-orange-600/40 text-orange-200 border-r border-orange-500/30"
            style={{ width: "16.7%" }}
            title="Critical Peak: ₹10.5/kWh (18:00–22:00)"
          >
            PEAK (₹10.5)
          </div>

          {/* 22:00 - 24:00: Standard Normal (8.3% of 24h) */}
          <div
            className="h-full bg-sky-600/25 text-sky-300"
            style={{ width: "8.3%" }}
            title="Normal: ₹7.0/kWh (22:00–24:00)"
          >
            NORMAL
          </div>
        </div>
      </div>
    </div>
  );
}
