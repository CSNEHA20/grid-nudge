"use client";

import { useState, useEffect, useMemo } from "react";
import { Zap, ChevronDown } from "lucide-react";
import { ConcentricGauge } from "./ConcentricGauge";
import { ConfidenceRings } from "./ConfidenceRings";
import { AttentionBudget } from "./AttentionBudget";
import { FleetLoadCard } from "./FleetLoadCard";
import { PeakReductionCircle } from "./PeakReductionCircle";
import { MetricsSummary } from "./MetricsSummary";
import { EventInjector, EventType } from "./EventInjector";
import { SafetyVetoAlert } from "./SafetyVetoAlert";
import { FloatingDock } from "./FloatingDock";
import { FleetLoadChartModal } from "./FleetLoadChartModal";
import { TimelineData } from "@/lib/data";

interface LiveViewProps {
  initialTimeline: TimelineData;
}

export function LiveView({ initialTimeline }: LiveViewProps) {
  // Scenario selector
  const [scenario, setScenario] = useState<string>("Heatwave");
  const [activeEvent, setActiveEvent] = useState<EventType>("heatwave");

  // Replay timeline step (index 0 to 95 for 15-min increments across 24h)
  // Step 74 corresponds to 18:30–18:45 (peak evening window)
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(74);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [showFullChart, setShowFullChart] = useState<boolean>(false);

  const timesteps = initialTimeline.timesteps || [];
  const currentStep = timesteps[currentStepIndex] || timesteps[74] || {
    step: 74,
    sim_time: "2026-10-10T18:45:00+05:30",
    hour: 18.75,
    is_peak_window: true,
    feeder_capacity_mw: 12.0,
    base_load_mw: 7.8,
    solar_gen_mw: 0.0,
    baseline_ev_load_mw: 6.4,
    gridnudge_ev_load_mw: 3.7,
    baseline_total_load_mw: 14.2,
    gridnudge_total_load_mw: 11.5,
    baseline_stress: 1.18,
    gridnudge_stress: 0.96,
    nudges_delivered: 320,
    safety_vetoes: 37,
    learned_silence_count: 580,
    shadow_price_inr: 12.5,
  };

  // Auto-play timer for replay scrub
  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | undefined;
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentStepIndex((prev) => (prev + 1) % timesteps.length);
      }, 1200);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, timesteps.length]);

  // Handle Event Injection
  const handleSelectEvent = (event: EventType) => {
    setActiveEvent(event);
    if (event === "heatwave") setScenario("Heatwave");
    else if (event === "solar_drop") setScenario("Solar Drop");
    else if (event === "station_outage") setScenario("Station Outage");
  };

  // Derived metrics for UI
  const broadcastPct = Math.round((currentStep.baseline_stress || 1.18) * 100);
  const gridnudgePct = Math.round((currentStep.gridnudge_stress || 0.96) * 100);
  const peakReductionPct = 14.2;
  const currentMw = currentStep.gridnudge_total_load_mw || 4.1;

  // Format Sim Time (e.g. 18:42)
  const formattedTime = useMemo(() => {
    try {
      const d = new Date(currentStep.sim_time);
      const hours = d.getHours().toString().padStart(2, "0");
      const mins = d.getMinutes().toString().padStart(2, "0");
      return `${hours}:${mins}`;
    } catch {
      return "18:42";
    }
  }, [currentStep.sim_time]);

  return (
    <div className="w-full flex flex-col gap-6 pt-2 pb-8">
      {/* Top micro-bar: Time & Date pills */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label="Simulation state"
          className="w-10 h-10 rounded-full bg-navy-800/90 border border-slate-700/60 flex items-center justify-center text-slate-300 hover:text-white transition"
        >
          <Zap className="w-4 h-4 text-nudge-gold" />
        </button>

        <div className="px-5 py-2 rounded-full bg-navy-800/90 border border-slate-700/60 font-mono text-sm font-semibold text-white tracking-wider shadow-sm">
          {formattedTime}
        </div>

        <div className="px-5 py-2 rounded-full bg-navy-800/90 border border-slate-700/60 text-sm font-medium text-slate-200 shadow-sm">
          Sat, 10 Oct
        </div>

        {/* Live Replay Scrubber (subtle timeline bar) */}
        <div className="flex-1 hidden md:flex items-center gap-3 px-4 py-2 rounded-full bg-navy-900/60 border border-slate-800/60">
          <span className="text-[11px] font-mono text-slate-400">Step {currentStepIndex}/95</span>
          <input
            type="range"
            min={0}
            max={timesteps.length - 1 || 95}
            value={currentStepIndex}
            onChange={(e) => setCurrentStepIndex(Number(e.target.value))}
            className="flex-1 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-nudge-gold"
          />
          <span className="text-[11px] font-mono text-slate-400">
            {currentStep.is_peak_window ? "PEAK (18:00-22:00)" : "OFF-PEAK"}
          </span>
        </div>
      </div>

      {/* Main 3-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (Width 3/12) */}
        <div className="lg:col-span-3 flex flex-col gap-4">
          {/* Card 1: Fleet Load */}
          <FleetLoadCard
            currentMw={currentMw}
            timeToPeak="0h 18m"
            onClick={() => setShowFullChart(true)}
          />

          {/* Card 2: Confidence Rings */}
          <ConfidenceRings journeyPct={94} chargingPct={91} />

          {/* Card 3: Attention Budget */}
          <AttentionBudget usedPct={62} />

          {/* Scenario Selector Dropdown */}
          <div className="relative mt-2">
            <button
              type="button"
              className="w-full flex items-center justify-between p-2.5 rounded-full bg-navy-800/90 border border-slate-700/60 hover:border-slate-500 transition group shadow-md"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-orange-600 text-white font-bold text-xs flex items-center justify-center shadow-sm">
                  VS
                </div>
                <span className="text-sm font-semibold text-slate-200">
                  Replay · {scenario}
                </span>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-400 group-hover:text-white mr-2" />
            </button>
          </div>
        </div>

        {/* Center Column: Massive Radial Feeder Gauge (Width 6/12) */}
        <div className="lg:col-span-6 flex flex-col items-center justify-center pt-2">
          {/* Feeder Zone Pill */}
          <div className="flex items-center gap-2 px-5 py-2 rounded-full bg-navy-800/90 border border-slate-700/60 mb-6 shadow-md">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500 animate-pulse" />
            <span className="text-sm font-semibold text-slate-100">
              Feeder zone 7 · Delhi
            </span>
          </div>

          {/* Massive Concentric Dual Radial Gauge */}
          <div className="my-2">
            <ConcentricGauge
              broadcastPct={broadcastPct}
              gridnudgePct={gridnudgePct}
            />
          </div>

          {/* Sub-legend pills below gauge */}
          <div className="flex items-center gap-4 mt-8 mb-8">
            <div className="flex items-center gap-2 px-5 py-2 rounded-full bg-navy-800/90 border border-slate-700/60 shadow-md">
              <span className="w-3 h-3 rounded-full bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.6)]" />
              <span className="text-sm font-medium text-slate-200">
                Broadcast {broadcastPct}%
              </span>
            </div>

            <div className="flex items-center gap-2 px-5 py-2 rounded-full bg-navy-800/90 border border-slate-700/60 shadow-md">
              <span className="w-3 h-3 rounded-full bg-nudge-gold shadow-[0_0_8px_rgba(250,204,21,0.6)]" />
              <span className="text-sm font-semibold text-white">
                GridNudge {gridnudgePct}%
              </span>
            </div>
          </div>

          {/* Floating Dock Controls */}
          <FloatingDock
            isPlaying={isPlaying}
            onTogglePlay={() => setIsPlaying(!isPlaying)}
            showFullChart={showFullChart}
            onToggleFullChart={() => setShowFullChart(!showFullChart)}
          />
        </div>

        {/* Right Column (Width 3/12) */}
        <div className="lg:col-span-3 flex flex-col gap-5">
          {/* Hero Circular Peak Reduction Card */}
          <PeakReductionCircle
            reductionPct={peakReductionPct}
            seedCount={10}
          />

          {/* Metrics Summary Card */}
          <MetricsSummary
            nudgesPerUser={0.8}
            broadcastNudges={4.0}
            vetoedCount={37}
            silentPct={71}
            strandedCount={0}
          />

          {/* Event Injector */}
          <div className="my-1">
            <EventInjector
              activeEvent={activeEvent}
              onSelectEvent={handleSelectEvent}
            />
          </div>

          {/* Safety Veto Alert bottom right ticker */}
          <div className="mt-1">
            <SafetyVetoAlert
              userId="u_2310"
              condition="journey_conf_lb 0.82 < 0.90"
              decisionId="d_002_safety_veto"
            />
          </div>
        </div>
      </div>

      {/* Full 24-hour fleet load chart modal */}
      <FleetLoadChartModal
        isOpen={showFullChart}
        onClose={() => setShowFullChart(false)}
        timesteps={timesteps}
      />
    </div>
  );
}
