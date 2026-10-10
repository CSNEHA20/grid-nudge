"use client";

import { Activity } from "lucide-react";

interface FleetLoadCardProps {
  currentMw?: number;
  timeToPeak?: string;
  loadBars?: number[];
  onClick?: () => void;
}

export function FleetLoadCard({
  currentMw = 4.1,
  timeToPeak = "0h 18m",
  loadBars = [
    30, 45, 55, 40, 75, 90, 85, 95, 60, 45, 70, 80, 100, 85, 65, 45, 55, 40, 60,
    75, 90, 80, 60, 50,
  ],
  onClick,
}: FleetLoadCardProps) {
  return (
    <div
      onClick={onClick}
      className="p-4 rounded-2xl glass-panel-interactive cursor-pointer group"
    >
      {/* Title */}
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-slate-300 group-hover:text-nudge-gold transition" />
        <span className="text-sm font-semibold text-slate-200 tracking-tight">
          Fleet load
        </span>
      </div>

      {/* Sparkline Vertical Bars */}
      <div className="h-10 flex items-end justify-between gap-[3px] px-1 mb-3">
        {loadBars.map((val, idx) => {
          const isHigh = val > 75;
          return (
            <div
              key={idx}
              className={`w-full rounded-sm transition-all duration-300 ${
                isHigh
                  ? "bg-amber-400 group-hover:bg-nudge-gold"
                  : "bg-slate-300/80 group-hover:bg-slate-200"
              }`}
              style={{ height: `${Math.max(val * 0.9, 15)}%` }}
            />
          );
        })}
      </div>

      {/* Metric readout */}
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-extrabold text-white tracking-tight">
          {currentMw.toFixed(1)}
        </span>
        <span className="text-xs text-slate-400 font-medium">
          MW now · peak window in {timeToPeak}
        </span>
      </div>
    </div>
  );
}
