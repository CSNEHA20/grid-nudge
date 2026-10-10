"use client";

interface ConcentricGaugeProps {
  broadcastPct: number;
  gridnudgePct: number;
}

export function ConcentricGauge({
  broadcastPct = 118,
  gridnudgePct = 96,
}: ConcentricGaugeProps) {
  const size = 380;
  const strokeWidth = 14;
  const center = size / 2;

  // Outer ring: Broadcast load (e.g. 118% -> cap visual at 100% or show overload break)
  const outerRadius = 145;
  const outerCircumference = 2 * Math.PI * outerRadius;
  const outerNormalized = Math.min(broadcastPct, 120) / 100;
  const outerDashoffset = outerCircumference * (1 - Math.min(outerNormalized, 1.0));

  // Inner ring: GridNudge load (96%)
  const innerRadius = 120;
  const innerCircumference = 2 * Math.PI * innerRadius;
  const innerNormalized = Math.min(gridnudgePct, 120) / 100;
  const innerDashoffset = innerCircumference * (1 - innerNormalized);

  return (
    <div className="relative flex items-center justify-center w-[340px] h-[340px] sm:w-[380px] sm:h-[380px] select-none">
      {/* Outer circular dotted boundary guide */}
      <svg
        className="absolute inset-0 w-full h-full transform -rotate-90"
        viewBox={`0 0 ${size} ${size}`}
      >
        <circle
          cx={center}
          cy={center}
          r={outerRadius + 22}
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
          stroke="rgba(249, 115, 22, 0.15)"
          strokeWidth={strokeWidth}
        />

        {/* Outer Ring Active (Broadcast - Orange) */}
        <circle
          cx={center}
          cy={center}
          r={outerRadius}
          fill="none"
          stroke="url(#orangeGradient)"
          strokeWidth={strokeWidth}
          strokeDasharray={outerCircumference}
          strokeDashoffset={outerDashoffset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />

        {/* Inner Ring Background (Track) */}
        <circle
          cx={center}
          cy={center}
          r={innerRadius}
          fill="none"
          stroke="rgba(250, 204, 21, 0.15)"
          strokeWidth={strokeWidth}
        />

        {/* Inner Ring Active (GridNudge - Yellow) */}
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
          className="transition-all duration-1000 ease-out"
        />

        {/* Gradients */}
        <defs>
          <linearGradient id="orangeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ea580c" />
            <stop offset="50%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#fb923c" />
          </linearGradient>
          <linearGradient id="yellowGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#eab308" />
            <stop offset="60%" stopColor="#facc15" />
            <stop offset="100%" stopColor="#fef08a" />
          </linearGradient>
        </defs>
      </svg>

      {/* Center Centerpiece */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center">
        <span className="text-xs uppercase tracking-wider text-slate-400 font-medium mb-0.5">
          Feeder load
        </span>
        <div className="flex items-baseline justify-center">
          <span className="text-6xl sm:text-7xl font-extrabold tracking-tight text-white drop-shadow-md">
            {gridnudgePct}
          </span>
          <span className="text-3xl font-bold text-nudge-yellow ml-0.5">%</span>
        </div>
        <span className="text-xs text-slate-400 font-medium mt-1">
          of capacity at peak
        </span>
      </div>
    </div>
  );
}
