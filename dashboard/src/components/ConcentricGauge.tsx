"use client";

import { useState } from "react";

interface ConcentricGaugeProps {
  broadcastPct: number;
  gridnudgePct: number;
  capacityMw?: number;
  isolatedSeries?: "all" | "broadcast" | "gridnudge";
}

export function ConcentricGauge({
  broadcastPct = 118,
  gridnudgePct = 96,
  capacityMw = 12.0,
  isolatedSeries = "all",
}: ConcentricGaugeProps) {
  const [hoveredSeries, setHoveredSeries] = useState<"broadcast" | "gridnudge" | null>(null);

  const size = 380;
  const strokeWidth = 14;
  const center = size / 2;

  // Outer ring: Broadcast load (118%)
  const outerRadius = 145;
  const outerCircumference = 2 * Math.PI * outerRadius;

  // Base portion (up to 100%)
  const outerBaseRatio = Math.min(broadcastPct, 100) / 100;
  const outerBaseOffset = outerCircumference * (1 - outerBaseRatio);

  // Overshoot portion (above 100%, up to 130%)
  const hasOvershoot = broadcastPct > 100;
  const overshootRatio = hasOvershoot ? (broadcastPct - 100) / 100 : 0;
  // Circumference length for overshoot
  const overshootLength = outerCircumference * overshootRatio;

  // Inner ring: GridNudge load (96%)
  const innerRadius = 118;
  const innerCircumference = 2 * Math.PI * innerRadius;
  const innerNormalized = Math.min(gridnudgePct, 120) / 100;
  const innerDashoffset = innerCircumference * (1 - innerNormalized);

  // Calculate MW values
  const broadcastMw = ((broadcastPct / 100) * capacityMw).toFixed(1);
  const gridnudgeMw = ((gridnudgePct / 100) * capacityMw).toFixed(1);

  // Opacities based on isolatedSeries or hover
  const showBroadcast = isolatedSeries === "all" || isolatedSeries === "broadcast";
  const showGridnudge = isolatedSeries === "all" || isolatedSeries === "gridnudge";

  return (
    <div className="relative flex items-center justify-center w-[340px] h-[340px] sm:w-[380px] sm:h-[380px] select-none">
      <svg
        className="absolute inset-0 w-full h-full transform -rotate-90"
        viewBox={`0 0 ${size} ${size}`}
      >
        {/* 100% Capacity reference guide line */}
        <circle
          cx={center}
          cy={center}
          r={outerRadius + 20}
          fill="none"
          stroke="rgba(255, 255, 255, 0.08)"
          strokeWidth="1.5"
          strokeDasharray="4 6"
        />

        {/* Outer Ring Background (Track) */}
        <circle
          cx={center}
          cy={center}
          r={outerRadius}
          fill="none"
          stroke="rgba(249, 115, 22, 0.12)"
          strokeWidth={strokeWidth}
        />

        {/* Outer Ring Active (Broadcast base up to 100%) */}
        {showBroadcast && (
          <circle
            cx={center}
            cy={center}
            r={outerRadius}
            fill="none"
            stroke="url(#orangeGradient)"
            strokeWidth={strokeWidth}
            strokeDasharray={outerCircumference}
            strokeDashoffset={outerBaseOffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out cursor-pointer"
            onMouseEnter={() => setHoveredSeries("broadcast")}
            onMouseLeave={() => setHoveredSeries(null)}
          />
        )}

        {/* Outer Ring Overshoot (>100% capacity violation in glowing red/amber) */}
        {showBroadcast && hasOvershoot && (
          <circle
            cx={center}
            cy={center}
            r={outerRadius}
            fill="none"
            stroke="#ef4444"
            strokeWidth={strokeWidth + 2}
            strokeDasharray={`${overshootLength} ${outerCircumference}`}
            strokeDashoffset={-outerCircumference * 0} // starts at 100%
            strokeLinecap="round"
            className="transition-all duration-700 ease-out cursor-pointer animate-pulse drop-shadow-[0_0_8px_rgba(239,68,68,0.8)]"
            onMouseEnter={() => setHoveredSeries("broadcast")}
            onMouseLeave={() => setHoveredSeries(null)}
          />
        )}

        {/* Inner Ring Background (Track) */}
        <circle
          cx={center}
          cy={center}
          r={innerRadius}
          fill="none"
          stroke="rgba(250, 204, 21, 0.12)"
          strokeWidth={strokeWidth}
        />

        {/* Inner Ring Active (GridNudge - Yellow) */}
        {showGridnudge && (
          <circle
            cx={center}
            cy={center}
            r={innerRadius}
            fill="none"
            stroke="url(#yellowGradient)"
            strokeWidth={strokeWidth}
            strokeDasharray={innerCircumference}
            strokeDashoffset={innerDashoffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out cursor-pointer"
            onMouseEnter={() => setHoveredSeries("gridnudge")}
            onMouseLeave={() => setHoveredSeries(null)}
          />
        )}

        {/* 100% Capacity tick mark at top (rotated -90deg so angle 0 is top) */}
        <line
          x1={center + outerRadius - 12}
          y1={center}
          x2={center + outerRadius + 12}
          y2={center}
          stroke="#ffffff"
          strokeWidth="2.5"
          opacity="0.8"
        />

        {/* Gradients */}
        <defs>
          <linearGradient id="orangeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ea580c" />
            <stop offset="50%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#fb923c" />
          </linearGradient>
          <linearGradient id="yellowGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ca8a04" />
            <stop offset="50%" stopColor="#facc15" />
            <stop offset="100%" stopColor="#fef08a" />
          </linearGradient>
        </defs>
      </svg>

      {/* Center Centerpiece */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center">
        {hoveredSeries === "broadcast" ? (
          <div className="animate-in fade-in duration-150">
            <span className="text-[11px] uppercase tracking-wider text-orange-400 font-semibold mb-0.5 block">
              Broadcast Baseline
            </span>
            <div className="flex items-baseline justify-center">
              <span className="text-5xl sm:text-6xl font-extrabold tracking-tight text-white drop-shadow-md">
                {broadcastPct}
              </span>
              <span className="text-2xl font-bold text-orange-400 ml-0.5">%</span>
            </div>
            <span className="text-xs text-orange-300 font-mono mt-1 block">
              {broadcastMw} MW / {capacityMw} MW ({hasOvershoot ? "Overshoot!" : "Safe"})
            </span>
          </div>
        ) : hoveredSeries === "gridnudge" ? (
          <div className="animate-in fade-in duration-150">
            <span className="text-[11px] uppercase tracking-wider text-nudge-gold font-semibold mb-0.5 block">
              GridNudge Staggered
            </span>
            <div className="flex items-baseline justify-center">
              <span className="text-5xl sm:text-6xl font-extrabold tracking-tight text-white drop-shadow-md">
                {gridnudgePct}
              </span>
              <span className="text-2xl font-bold text-nudge-gold ml-0.5">%</span>
            </div>
            <span className="text-xs text-amber-200 font-mono mt-1 block">
              {gridnudgeMw} MW / {capacityMw} MW (Within bounds)
            </span>
          </div>
        ) : (
          <div>
            <span className="text-xs uppercase tracking-wider text-slate-300 font-medium mb-0.5 block">
              Feeder load
            </span>
            <div className="flex items-baseline justify-center">
              <span className="text-6xl sm:text-7xl font-extrabold tracking-tight text-white drop-shadow-md">
                {gridnudgePct}
              </span>
              <span className="text-3xl font-bold text-nudge-gold ml-0.5">%</span>
            </div>
            <span className="text-xs text-slate-400 font-medium mt-1 block">
              of capacity at peak
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
