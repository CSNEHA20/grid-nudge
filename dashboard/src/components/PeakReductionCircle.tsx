"use client";

interface PeakReductionCircleProps {
  reductionPct?: number;
  seedCount?: number;
}

export function PeakReductionCircle({
  reductionPct = 14.2,
  seedCount = 10,
}: PeakReductionCircleProps) {
  return (
    <div className="relative flex flex-col items-center justify-center p-6 rounded-full aspect-square w-64 h-64 mx-auto glass-panel border border-amber-400/25 shadow-glow">
      {/* Outer ambient glow ring */}
      <div className="absolute inset-2 rounded-full border border-amber-500/20" />
      <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-amber-500/10 via-transparent to-yellow-400/15" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center">
        <span className="text-xs uppercase tracking-wider text-slate-300 font-medium mb-1">
          Peak reduction
        </span>
        <span className="text-5xl font-black text-white tracking-tight drop-shadow-md">
          -{reductionPct.toFixed(1)}%
        </span>
        <span className="text-xs text-slate-400 font-medium mt-1">
          vs broadcast · {seedCount} seeds
        </span>
      </div>
    </div>
  );
}
