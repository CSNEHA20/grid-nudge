"use client";

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
  return (
    <div className="flex flex-col items-center text-center p-4 rounded-2xl glass-panel">
      <span className="text-xs uppercase tracking-wider text-slate-300 font-medium">
        Nudges / user / day
      </span>
      <div className="flex items-baseline gap-2 mt-1 mb-4">
        <span className="text-4xl font-extrabold text-white tracking-tight">
          {nudgesPerUser.toFixed(1)}
        </span>
        <span className="text-xs font-mono text-slate-400">
          vs {broadcastNudges.toFixed(1)}
        </span>
      </div>

      {/* 3 Pill counters */}
      <div className="grid grid-cols-3 gap-3 w-full">
        {/* Vetoed */}
        <div className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-navy-900/80 border border-slate-700/50">
          <span className="text-xl font-bold text-white tracking-tight">
            {vetoedCount}
          </span>
          <span className="text-[10px] uppercase font-medium text-slate-400 mt-0.5">
            vetoed
          </span>
        </div>

        {/* Silent */}
        <div className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-navy-900/80 border border-slate-700/50">
          <span className="text-xl font-bold text-white tracking-tight">
            {silentPct}%
          </span>
          <span className="text-[10px] uppercase font-medium text-slate-400 mt-0.5">
            silent
          </span>
        </div>

        {/* Stranded */}
        <div className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-navy-900/80 border border-slate-700/50">
          <span className="text-xl font-bold text-nudge-yellow tracking-tight">
            {strandedCount}
          </span>
          <span className="text-[10px] uppercase font-medium text-slate-400 mt-0.5">
            stranded
          </span>
        </div>
      </div>
    </div>
  );
}
