"use client";

import Link from "next/link";
import { useState } from "react";
import { Info } from "lucide-react";
import { METRIC_GLOSSARY } from "@/lib/glossary";

interface MetricsSummaryProps {
  nudgesPerUser?: number;
  broadcastNudges?: number;
  vetoedCount?: number;
  silentPct?: number;
  strandedCount?: number;
}

export function MetricsSummary({
  nudgesPerUser = 0.8,
  broadcastNudges = 4.0,
  vetoedCount = 37,
  silentPct = 71,
  strandedCount = 0,
}: MetricsSummaryProps) {
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null);

  return (
    <div className="relative flex flex-col items-center text-center p-4 rounded-2xl glass-panel">
      {/* Header with info tooltip */}
      <div className="flex items-center gap-1.5 mb-0.5">
        <span className="text-xs uppercase tracking-wider text-slate-300 font-semibold">
          Nudges / user / day
        </span>
        <button
          type="button"
          aria-label="Attention cost info"
          onMouseEnter={() => setActiveTooltip("nudges")}
          onMouseLeave={() => setActiveTooltip(null)}
          className="text-slate-400 hover:text-white transition"
        >
          <Info className="w-3 h-3" />
        </button>
      </div>

      {activeTooltip === "nudges" && (
        <div className="absolute top-10 z-30 w-52 p-2 rounded-lg bg-navy-900/95 border border-slate-700 text-[11px] text-slate-200 shadow-xl backdrop-blur-md">
          {METRIC_GLOSSARY.nudgesPerUserDay}
        </div>
      )}

      {/* Main Stat */}
      <div className="flex items-baseline gap-2 mt-1 mb-4">
        <span className="text-4xl font-extrabold text-white tracking-tight">
          {nudgesPerUser.toFixed(1)}
        </span>
        <span className="text-xs font-mono text-slate-400">
          vs {broadcastNudges.toFixed(1)} broadcast
        </span>
      </div>

      {/* 3 Pill counters */}
      <div className="grid grid-cols-3 gap-2.5 w-full">
        {/* Vetoed */}
        <Link
          href="/decisions?status=vetoed"
          title="Filter vetoed decisions"
          className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-navy-900/80 border border-slate-700/50 hover:border-sky-400/60 transition group cursor-pointer"
        >
          <span className="text-xl font-bold text-white group-hover:text-sky-300 tracking-tight transition">
            {vetoedCount}
          </span>
          <span className="text-[10px] uppercase font-semibold text-slate-400 group-hover:text-slate-200 mt-0.5 transition">
            vetoed
          </span>
        </Link>

        {/* Silent */}
        <Link
          href="/decisions?status=silent"
          title="Filter learned silence decisions"
          className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-navy-900/80 border border-slate-700/50 hover:border-amber-400/60 transition group cursor-pointer"
        >
          <span className="text-xl font-bold text-white group-hover:text-nudge-gold tracking-tight transition">
            {silentPct}%
          </span>
          <span className="text-[10px] uppercase font-semibold text-slate-400 group-hover:text-slate-200 mt-0.5 transition">
            silent
          </span>
        </Link>

        {/* Stranded */}
        <div
          title={METRIC_GLOSSARY.strandedTrips}
          className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-navy-900/80 border border-amber-500/30 group"
        >
          <span className="text-xl font-bold text-nudge-gold tracking-tight drop-shadow-sm">
            {strandedCount}
          </span>
          <span className="text-[10px] uppercase font-semibold text-amber-300/90 mt-0.5">
            stranded
          </span>
        </div>
      </div>
    </div>
  );
}
