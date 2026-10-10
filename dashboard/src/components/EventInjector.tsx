"use client";

import { useState } from "react";
import { Flame, Sun, ZapOff, DollarSign, X, Check } from "lucide-react";

export type EventType = "heatwave" | "solar_drop" | "station_outage" | "tariff_change" | "none";

interface EventConfig {
  type: EventType;
  title: string;
  description: string;
  params: Record<string, string>;
}

const EVENT_CONFIGS: Record<Exclude<EventType, "none">, EventConfig> = {
  heatwave: {
    type: "heatwave",
    title: "Inject Heatwave Stress",
    description: "Increases residential baseline AC cooling demand and shifts peak load higher.",
    params: {
      "Start time": "14:00 IST",
      "Temperature offset": "+3.5°C",
      "Baseline load multiplier": "1.25×",
      "Feeder peak": "14.2 MW (>100% capacity)",
    },
  },
  solar_drop: {
    type: "solar_drop",
    title: "Inject Solar Generation Drop",
    description: "Simulates sudden heavy cloud cover dropping rooftop PV generation midday.",
    params: {
      "Window": "11:00 – 15:00 IST",
      "Generation drop": "-40% solar PV",
      "Green charging window": "Shrunk to 2.5 hours",
    },
  },
  station_outage: {
    type: "station_outage",
    title: "Inject Station Outage",
    description: "Simulates grid fault taking South Delhi hub off-line, causing queue buildup.",
    params: {
      "Affected station": "Hub #4 (South Extension)",
      "Duration": "4 hours (17:00 – 21:00)",
      "Queue wait impact": "+28 min expected ETA wait",
    },
  },
  tariff_change: {
    type: "tariff_change",
    title: "Inject Peak Tariff Hike",
    description: "Simulates dynamic critical-peak pricing multiplier implemented by DISCOM.",
    params: {
      "Peak window": "18:00 – 22:00 IST",
      "Peak tariff multiplier": "1.50× (₹12.5/kWh)",
      "Off-peak incentive": "₹4.5/kWh discount",
    },
  },
};

interface EventInjectorProps {
  activeEvent: EventType;
  onSelectEvent: (event: EventType) => void;
}

export function EventInjector({
  activeEvent,
  onSelectEvent,
}: EventInjectorProps) {
  const [pendingEvent, setPendingEvent] = useState<EventType | null>(null);

  const handleOpenConfirm = (event: EventType) => {
    if (activeEvent === event) {
      // Toggle off / clear if already active
      onSelectEvent("none");
    } else {
      setPendingEvent(event);
    }
  };

  const handleConfirm = () => {
    if (pendingEvent) {
      onSelectEvent(pendingEvent);
      setPendingEvent(null);
    }
  };

  return (
    <div className="relative flex flex-col items-center">
      {/* Event button ring */}
      <div className="flex items-center gap-3">
        {/* Heatwave Button */}
        <button
          type="button"
          onClick={() => handleOpenConfirm("heatwave")}
          aria-label="Inject Heatwave"
          title="Inject Heatwave (+3.5°C, 1.25x base load)"
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 relative ${
            activeEvent === "heatwave"
              ? "bg-[#c2410c] text-white shadow-glow-orange ring-2 ring-orange-400 scale-105"
              : "bg-navy-800/90 text-slate-400 hover:text-white border border-slate-700/60 hover:border-slate-500"
          }`}
        >
          <Flame className="w-5 h-5 fill-current" />
          {activeEvent === "heatwave" && (
            <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-orange-400 animate-ping" />
          )}
        </button>

        {/* Solar Drop Button */}
        <button
          type="button"
          onClick={() => handleOpenConfirm("solar_drop")}
          aria-label="Inject Solar Drop"
          title="Inject Solar Drop (-40% PV)"
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 relative ${
            activeEvent === "solar_drop"
              ? "bg-amber-600 text-white shadow-glow ring-2 ring-amber-400 scale-105"
              : "bg-navy-800/90 text-slate-400 hover:text-white border border-slate-700/60 hover:border-slate-500"
          }`}
        >
          <Sun className="w-5 h-5 fill-current" />
          {activeEvent === "solar_drop" && (
            <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-amber-400 animate-ping" />
          )}
        </button>

        {/* Station Outage Button */}
        <button
          type="button"
          onClick={() => handleOpenConfirm("station_outage")}
          aria-label="Inject Station Outage"
          title="Inject Station Outage (Hub #4 offline)"
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 relative ${
            activeEvent === "station_outage"
              ? "bg-sky-600 text-white shadow-glow-cyan ring-2 ring-sky-400 scale-105"
              : "bg-navy-800/90 text-slate-400 hover:text-white border border-slate-700/60 hover:border-slate-500"
          }`}
        >
          <ZapOff className="w-5 h-5" />
          {activeEvent === "station_outage" && (
            <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-sky-400 animate-ping" />
          )}
        </button>

        {/* Tariff Change Button */}
        <button
          type="button"
          onClick={() => handleOpenConfirm("tariff_change")}
          aria-label="Inject Tariff Change"
          title="Inject Tariff Change (Critical peak 1.5x)"
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 relative ${
            activeEvent === "tariff_change"
              ? "bg-emerald-600 text-white shadow-glow ring-2 ring-emerald-400 scale-105"
              : "bg-navy-800/90 text-slate-400 hover:text-white border border-slate-700/60 hover:border-slate-500"
          }`}
        >
          <DollarSign className="w-5 h-5" />
          {activeEvent === "tariff_change" && (
            <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 animate-ping" />
          )}
        </button>
      </div>

      {/* Label & Active Event Badge */}
      <div className="flex items-center gap-2 mt-2">
        <span className="text-xs text-slate-400 font-medium">
          Inject event
        </span>
        {activeEvent !== "none" && (
          <button
            type="button"
            onClick={() => onSelectEvent("none")}
            className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-300 border border-orange-500/40 text-[10px] font-mono hover:bg-orange-500/30 transition"
          >
            <span>{activeEvent.replace("_", " ").toUpperCase()} ACTIVE</span>
            <X className="w-2.5 h-2.5 ml-0.5" />
          </button>
        )}
      </div>

      {/* Confirmation Modal Popover */}
      {pendingEvent && pendingEvent !== "none" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-sm rounded-2xl glass-panel p-5 border border-slate-700/80 shadow-2xl">
            <div className="flex items-start justify-between mb-3">
              <div>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-orange-500/20 text-orange-300 border border-orange-500/30">
                  Scenario Injection
                </span>
                <h3 className="text-base font-bold text-white mt-1.5">
                  {EVENT_CONFIGS[pendingEvent].title}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setPendingEvent(null)}
                aria-label="Cancel"
                className="w-7 h-7 rounded-full bg-navy-800 text-slate-400 hover:text-white flex items-center justify-center"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300 mb-4 leading-relaxed">
              {EVENT_CONFIGS[pendingEvent].description}
            </p>

            {/* Parameters list */}
            <div className="rounded-xl bg-navy-900/90 border border-slate-700/60 p-3 mb-4 space-y-1.5 text-xs">
              {Object.entries(EVENT_CONFIGS[pendingEvent].params).map(([k, v]) => (
                <div key={k} className="flex justify-between items-center">
                  <span className="text-slate-400">{k}</span>
                  <span className="font-mono text-slate-200 font-medium">{v}</span>
                </div>
              ))}
            </div>

            {/* Actions */}
            <div className="flex gap-2.5">
              <button
                type="button"
                onClick={() => setPendingEvent(null)}
                className="flex-1 py-2 rounded-xl bg-navy-800 hover:bg-navy-700 text-slate-300 text-xs font-semibold transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                className="flex-1 py-2 rounded-xl bg-orange-600 hover:bg-orange-500 text-white text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-md"
              >
                <Check className="w-3.5 h-3.5" />
                Inject Event
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
