"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import { METRIC_GLOSSARY } from "@/lib/glossary";

interface ConfidenceRingsProps {
  journeyPct?: number;
  chargingPct?: number;
}

export function ConfidenceRings({
  journeyPct = 94,
  chargingPct = 91,
}: ConfidenceRingsProps) {
  const [activeTooltip, setActiveTooltip] = useState<"journey" | "charging" | null>(null);

  // SVG circular calculation for Journey & Charging
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const chargingOffset = circumference * (1 - chargingPct / 100);

  // Generate 48 tick marks around Journey circle
  const tickCount = 48;
  const ticks = Array.from({ length: tickCount }, (_, i) => {
    const angle = (i * 360) / tickCount;
    const isLit = (i / tickCount) * 100 <= journeyPct;
    return { angle, isLit };
  });

  return (
    <div className="relative flex items-center justify-around gap-4 p-4 rounded-2xl glass-panel">
      {/* Tooltip display */}
      {activeTooltip && (
        <div className="absolute -top-16 left-4 right-4 z-30 p-2.5 rounded-xl bg-navy-900/95 border border-slate-700 text-[11px] text-slate-200 shadow-xl backdrop-blur-md">
          {activeTooltip === "journey" ? (
            <div>
              <span className="font-semibold text-sky-400 block mb-0.5">Fleet Journey Confidence</span>
              <span>{METRIC_GLOSSARY.fleetJourneyConfidence}</span>
            </div>
          ) : (
            <div>
              <span className="font-semibold text-nudge-gold block mb-0.5">Charging Confidence</span>
              <span>{METRIC_GLOSSARY.chargingConfidence}</span>
            </div>
          )}
        </div>
      )}

      {/* Journey Ring */}
      <div className="flex flex-col items-center">
        <div className="relative w-24 h-24 flex items-center justify-center">
          {/* Circular SVG ticks */}
          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100">
            {ticks.map(({ angle, isLit }, idx) => (
              <line
                key={idx}
                x1="50"
                y1="6"
                x2="50"
                y2="14"
                transform={`rotate(${angle} 50 50)`}
                stroke={isLit ? "#38bdf8" : "rgba(255, 255, 255, 0.12)"}
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            ))}
          </svg>
          <div className="flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-white tracking-tight">
              {journeyPct}%
            </span>
          </div>
        </div>

        <button
          type="button"
          onMouseEnter={() => setActiveTooltip("journey")}
          onMouseLeave={() => setActiveTooltip(null)}
          className="flex items-center gap-1 text-xs text-slate-400 hover:text-sky-300 font-medium mt-1 transition"
        >
          <span>Journey</span>
          <Info className="w-3 h-3" />
        </button>
      </div>

      {/* Charging Ring */}
      <div className="flex flex-col items-center">
        <div className="relative w-24 h-24 flex items-center justify-center">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
            {/* Background Track */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="rgba(250, 204, 21, 0.15)"
              strokeWidth="5.5"
            />
            {/* Progress Stroke */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="#facc15"
              strokeWidth="5.5"
              strokeDasharray={circumference}
              strokeDashoffset={chargingOffset}
              strokeLinecap="round"
              className="transition-all duration-700 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-white tracking-tight">
              {chargingPct}%
            </span>
          </div>
        </div>

        <button
          type="button"
          onMouseEnter={() => setActiveTooltip("charging")}
          onMouseLeave={() => setActiveTooltip(null)}
          className="flex items-center gap-1 text-xs text-slate-400 hover:text-nudge-gold font-medium mt-1 transition"
        >
          <span>Charging</span>
          <Info className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}
