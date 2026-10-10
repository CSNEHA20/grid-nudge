"use client";

import { Flame, Sun, ZapOff } from "lucide-react";

export type EventType = "heatwave" | "solar_drop" | "station_outage";

interface EventInjectorProps {
  activeEvent: EventType;
  onSelectEvent: (event: EventType) => void;
}

export function EventInjector({
  activeEvent,
  onSelectEvent,
}: EventInjectorProps) {
  return (
    <div className="flex flex-col items-center">
      <div className="flex items-center gap-4">
        {/* Heatwave Button */}
        <button
          type="button"
          onClick={() => onSelectEvent("heatwave")}
          aria-label="Inject Heatwave"
          className={`w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300 ${
            activeEvent === "heatwave"
              ? "bg-[#c2410c] text-white shadow-glow-orange ring-2 ring-orange-400 scale-105"
              : "bg-navy-800/90 text-slate-400 hover:text-white border border-slate-700/60 hover:border-slate-500"
          }`}
        >
          <Flame className="w-6 h-6 fill-current" />
        </button>

        {/* Solar Drop Button */}
        <button
          type="button"
          onClick={() => onSelectEvent("solar_drop")}
          aria-label="Inject Solar Drop"
          className={`w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300 ${
            activeEvent === "solar_drop"
              ? "bg-amber-600 text-white shadow-glow ring-2 ring-amber-400 scale-105"
              : "bg-navy-800/90 text-slate-400 hover:text-white border border-slate-700/60 hover:border-slate-500"
          }`}
        >
          <Sun className="w-6 h-6 fill-current" />
        </button>

        {/* Station Outage Button */}
        <button
          type="button"
          onClick={() => onSelectEvent("station_outage")}
          aria-label="Inject Station Outage"
          className={`w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300 ${
            activeEvent === "station_outage"
              ? "bg-sky-600 text-white shadow-glow-cyan ring-2 ring-sky-400 scale-105"
              : "bg-navy-800/90 text-slate-400 hover:text-white border border-slate-700/60 hover:border-slate-500"
          }`}
        >
          <ZapOff className="w-6 h-6" />
        </button>
      </div>

      <span className="text-xs text-slate-400 font-medium mt-2">
        Inject event
      </span>
    </div>
  );
}
