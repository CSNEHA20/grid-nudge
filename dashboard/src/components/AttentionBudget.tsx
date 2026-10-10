"use client";

import { Clock } from "lucide-react";

interface AttentionBudgetProps {
  usedPct?: number;
}

export function AttentionBudget({ usedPct = 62 }: AttentionBudgetProps) {
  return (
    <div className="p-4 rounded-2xl glass-panel">
      {/* Title */}
      <div className="flex items-center gap-2 mb-3">
        <Clock className="w-4 h-4 text-slate-300" />
        <span className="text-sm font-semibold text-slate-200 tracking-tight">
          Attention budget
        </span>
      </div>

      {/* Numerical markers */}
      <div className="flex justify-between items-center text-[11px] font-mono text-slate-400 mb-1.5 px-0.5">
        <span>0%</span>
        <span className="text-nudge-yellow font-semibold">{usedPct}%</span>
        <span>100%</span>
      </div>

      {/* Progress Bar Container */}
      <div className="relative w-full h-8 rounded-xl overflow-hidden bg-navy-900/90 border border-slate-700/60 flex">
        {/* Active Used Segment */}
        <div
          className="h-full bg-gradient-to-r from-orange-500 via-amber-400 to-yellow-300 shadow-[0_0_12px_rgba(250,204,21,0.35)] transition-all duration-700 ease-out"
          style={{ width: `${usedPct}%` }}
        />

        {/* Remaining Budget (Striped) */}
        <div
          className="h-full flex-1 bg-striped-pattern opacity-40"
          style={{ width: `${100 - usedPct}%` }}
        />
      </div>
    </div>
  );
}
