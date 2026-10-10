"use client";

import { useState } from "react";
import { Clock, Info } from "lucide-react";
import { METRIC_GLOSSARY } from "@/lib/glossary";

interface AttentionBudgetProps {
  usedPct?: number;
  shadowPrice?: number;
  rule?: string;
}

export function AttentionBudget({
  usedPct = 62,
  shadowPrice = 12.5,
  rule = "8% of plugged-in EVs per interval",
}: AttentionBudgetProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const isExhausted = usedPct >= 100;

  return (
    <div
      className={`relative p-4 rounded-2xl glass-panel transition-all ${
        isExhausted ? "border-orange-500/60 shadow-glow-orange" : ""
      }`}
    >
      {/* Title & Info */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-slate-300" />
          <span className="text-sm font-semibold text-slate-200 tracking-tight">
            Attention budget
          </span>
        </div>

        <button
          type="button"
          aria-label="Attention budget info"
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          className="text-slate-400 hover:text-white transition"
        >
          <Info className="w-3.5 h-3.5" />
        </button>
      </div>

      {showTooltip && (
        <div className="absolute top-10 right-4 z-30 w-56 p-2 rounded-lg bg-navy-900/95 border border-slate-700 text-[11px] text-slate-200 shadow-xl backdrop-blur-md">
          <p className="font-semibold text-nudge-gold mb-1">Attention Budget & Shadow Price</p>
          <p className="mb-1">{METRIC_GLOSSARY.attentionBudgetUsed}</p>
          <p className="text-slate-400 font-mono text-[10px]">{METRIC_GLOSSARY.shadowPrice}</p>
        </div>
      )}

      {/* Numerical markers & Shadow Price */}
      <div className="flex justify-between items-center text-[11px] font-mono text-slate-400 mb-1.5 px-0.5">
        <span>0%</span>
        <span
          className={`font-semibold ${
            isExhausted ? "text-orange-400 animate-pulse" : "text-nudge-gold"
          }`}
        >
          {usedPct}%
        </span>
        <span>100%</span>
      </div>

      {/* Progress Bar Container with Bubble Indicator */}
      <div className="relative w-full h-8 rounded-xl overflow-hidden bg-navy-900/90 border border-slate-700/60 flex items-center">
        {/* Active Used Segment */}
        <div
          className={`h-full transition-all duration-700 ease-out ${
            isExhausted
              ? "bg-gradient-to-r from-orange-600 to-red-500 shadow-[0_0_15px_rgba(239,68,68,0.5)]"
              : "bg-gradient-to-r from-orange-500 via-amber-400 to-yellow-300 shadow-[0_0_12px_rgba(250,204,21,0.35)]"
          }`}
          style={{ width: `${Math.min(usedPct, 100)}%` }}
        />

        {/* Bubble marker at the head of progress */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-white border-2 border-amber-400 shadow-md transition-all duration-700 pointer-events-none"
          style={{ left: `calc(${Math.min(usedPct, 96)}% - 8px)` }}
        />

        {/* Remaining Budget (Striped) */}
        <div
          className="h-full flex-1 bg-striped-pattern opacity-40"
          style={{ width: `${Math.max(100 - usedPct, 0)}%` }}
        />
      </div>

      {/* Sub-footer: Shadow Price & Budget Rule */}
      <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-slate-800 text-[11px]">
        <div className="flex items-center gap-1 text-slate-300">
          <span className="text-slate-400">Shadow price:</span>
          <span className="font-mono font-semibold text-nudge-gold">
            ₹{shadowPrice.toFixed(1)}/nudge
          </span>
        </div>
        <span className="text-[10px] text-slate-400 truncate max-w-[130px]" title={rule}>
          {rule}
        </span>
      </div>
    </div>
  );
}
