"use client";

import { useState } from "react";
import { ChevronDown, Info } from "lucide-react";
import { METRIC_GLOSSARY } from "@/lib/glossary";

export type ReferencePolicyKey = "B0" | "B1" | "B2" | "B3";

export interface PolicyOption {
  key: ReferencePolicyKey;
  label: string;
  reductionPct: number;
}

const POLICY_OPTIONS: PolicyOption[] = [
  { key: "B1", label: "Broadcast (B1)", reductionPct: 14.2 },
  { key: "B0", label: "No nudges (B0)", reductionPct: 18.5 },
  { key: "B2", label: "Rule-based (B2)", reductionPct: 9.8 },
  { key: "B3", label: "Plain bandit (B3)", reductionPct: 6.4 },
];

interface PeakReductionCircleProps {
  seedCount?: number;
}

export function PeakReductionCircle({
  seedCount = 10,
}: PeakReductionCircleProps) {
  const [selectedPolicy, setSelectedPolicy] = useState<ReferencePolicyKey>("B1");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const currentOption =
    POLICY_OPTIONS.find((p) => p.key === selectedPolicy) || POLICY_OPTIONS[0];

  return (
    <div className="relative flex flex-col items-center justify-center p-6 rounded-full aspect-square w-64 h-64 mx-auto glass-panel border border-amber-400/25 shadow-glow">
      {/* Outer ambient glow rings */}
      <div className="absolute inset-2 rounded-full border border-amber-500/20 pointer-events-none" />
      <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-amber-500/10 via-transparent to-yellow-400/15 pointer-events-none" />

      {/* Tooltip trigger */}
      <button
        type="button"
        aria-label="Metric definition"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className="absolute top-4 right-8 z-20 text-slate-400 hover:text-white transition"
      >
        <Info className="w-3.5 h-3.5" />
      </button>

      {showTooltip && (
        <div className="absolute top-10 right-4 z-30 w-56 p-2.5 rounded-xl bg-navy-900/95 border border-slate-700 text-[11px] text-slate-200 shadow-xl backdrop-blur-md">
          <p className="font-semibold text-nudge-gold mb-1">Peak Load Reduction %</p>
          <p className="text-slate-300 leading-relaxed">
            {METRIC_GLOSSARY.peakReduction}
          </p>
        </div>
      )}

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center">
        <span className="text-[11px] uppercase tracking-wider text-slate-300 font-semibold mb-0.5">
          Peak reduction
        </span>

        <span className="text-5xl font-black text-white tracking-tight drop-shadow-md">
          -{currentOption.reductionPct.toFixed(1)}%
        </span>

        {/* Policy dropdown selector */}
        <div className="relative mt-1">
          <button
            type="button"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-navy-800/80 hover:bg-navy-700/80 border border-slate-700/60 text-[11px] font-medium text-slate-300 hover:text-white transition"
          >
            <span>vs {currentOption.label}</span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>

          {isDropdownOpen && (
            <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1.5 w-44 rounded-xl bg-navy-900/95 border border-slate-700/80 shadow-2xl backdrop-blur-md overflow-hidden z-30 py-1">
              {POLICY_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => {
                    setSelectedPolicy(opt.key);
                    setIsDropdownOpen(false);
                  }}
                  className={`w-full px-3 py-1.5 text-left text-xs flex items-center justify-between transition ${
                    opt.key === selectedPolicy
                      ? "bg-amber-500/20 text-nudge-gold font-semibold"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <span>{opt.label}</span>
                  <span className="font-mono text-[11px]">-{opt.reductionPct}%</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <span className="text-[10px] text-slate-400 font-mono mt-1.5">
          {seedCount} seeds · Simulation
        </span>
      </div>
    </div>
  );
}
