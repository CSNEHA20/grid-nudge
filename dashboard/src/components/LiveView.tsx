"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import {
  Zap,
  ChevronDown,
  Maximize2,
  PieChart,
  TrendingUp,
  Play,
  Pause,
} from "lucide-react";
import { ConcentricGauge } from "./ConcentricGauge";
import { InlineTimelineChart } from "./InlineTimelineChart";
import { ConfidenceRings } from "./ConfidenceRings";
import { AttentionBudget } from "./AttentionBudget";
import { FleetLoadCard } from "./FleetLoadCard";
import { PeakReductionCircle } from "./PeakReductionCircle";
import { MetricsSummary } from "./MetricsSummary";
import { EventInjector, EventType } from "./EventInjector";
import { SafetyVetoAlert } from "./SafetyVetoAlert";
import { FloatingDock } from "./FloatingDock";
import { FleetLoadChartModal } from "./FleetLoadChartModal";
import { LiveDecisionTicker } from "./LiveDecisionTicker";
import { TimelineData } from "@/lib/data";

interface LiveViewProps {
  initialTimeline: TimelineData;
}

export function LiveView({ initialTimeline }: LiveViewProps) {
  // Scenario & Mode selection
  const [scenario, setScenario] = useState<string>("Heatwave");
  const [activeEvent, setActiveEvent] = useState<EventType>("heatwave");
  const [mode, setMode] = useState<"Replay" | "Live" | "Fixtures">("Replay");
  const [isScenarioDropdownOpen, setIsScenarioDropdownOpen] = useState(false);

  // Center hero view: "ring" or "timeline" per spec §5.1 L1
  const [heroView, setHeroView] = useState<"ring" | "timeline">("ring");
  const [isolatedSeries, setIsolatedSeries] = useState<"all" | "broadcast" | "gridnudge">("all");

  // Replay timeline step (index 0 to 95 for 15-min increments across 24h)
  // Step 75 corresponds to 18:45 (peak evening window)
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(75);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<1 | 4 | 16>(1);
  const [showFullChart, setShowFullChart] = useState<boolean>(false);

  const timesteps = useMemo(
    () => initialTimeline.timesteps || [],
    [initialTimeline.timesteps]
  );
  const currentStep = timesteps[currentStepIndex] || timesteps[75] || {
    step: 75,
    sim_time: "2026-10-10T18:45:00+05:30",
    hour: 18.75,
    is_peak_window: true,
    feeder_capacity_mw: 12.0,
    base_load_mw: 10.02,
    solar_gen_mw: 0.0,
    baseline_ev_load_mw: 5.15,
    gridnudge_ev_load_mw: 1.2,
    baseline_total_load_mw: 15.17,
    gridnudge_total_load_mw: 11.22,
    baseline_stress: 1.264,
    gridnudge_stress: 0.935,
    nudges_delivered: 42,
    safety_vetoes: 6,
    learned_silence_count: 28,
    shadow_price_inr: 14.5,
  };

  // Keyboard navigation per spec §4.3: Space=play/pause, ArrowLeft/Right=step, [ ]=markers
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.code === "Space") {
        e.preventDefault();
        setIsPlaying((prev) => !prev);
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        setCurrentStepIndex((prev) => Math.max(0, prev - 1));
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        setCurrentStepIndex((prev) => Math.min(timesteps.length - 1, prev + 1));
      } else if (e.key === "[") {
        // Jump to previous marker (event start at step 56 or 0)
        e.preventDefault();
        setCurrentStepIndex(56);
      } else if (e.key === "]") {
        // Jump to peak window marker (step 75)
        e.preventDefault();
        setCurrentStepIndex(75);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [timesteps.length]);

  // Auto-play timer for replay scrubber
  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | undefined;
    if (isPlaying) {
      const intervalMs = Math.max(1200 / playbackSpeed, 100);
      timer = setInterval(() => {
        setCurrentStepIndex((prev) => {
          if (prev >= timesteps.length - 1) {
            return 0; // loop back to midnight
          }
          return prev + 1;
        });
      }, intervalMs);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, playbackSpeed, timesteps.length]);

  // Handle Event Injection
  const handleSelectEvent = (event: EventType) => {
    setActiveEvent(event);
    if (event === "heatwave") setScenario("Heatwave");
    else if (event === "solar_drop") setScenario("Solar Drop");
    else if (event === "station_outage") setScenario("Station Outage");
    else if (event === "tariff_change") setScenario("Tariff Hike");
    else if (event === "none") setScenario("Standard Baseline");
  };

  // Quick jumps per spec §4.3
  const jumpToPeak = useCallback(() => setCurrentStepIndex(75), []);
  const jumpToVeto = useCallback(() => setCurrentStepIndex(77), []);
  const jumpToEvent = useCallback(() => setCurrentStepIndex(56), []);

  // Derived metrics for UI
  const broadcastPct = Math.round((currentStep.baseline_stress || 1.18) * 100);
  const gridnudgePct = Math.round((currentStep.gridnudge_stress || 0.96) * 100);
  const currentMw = currentStep.gridnudge_total_load_mw || 11.2;
  const shadowPrice = currentStep.shadow_price_inr || 12.5;

  // Format Sim Time (e.g. 18:45)
  const formattedTime = useMemo(() => {
    try {
      const d = new Date(currentStep.sim_time);
      const hours = d.getHours().toString().padStart(2, "0");
      const mins = d.getMinutes().toString().padStart(2, "0");
      return `${hours}:${mins}`;
    } catch {
      return "18:45";
    }
  }, [currentStep.sim_time]);

  // Countdown to peak window (18:00 to 22:00)
  const timeToPeakText = useMemo(() => {
    if (currentStep.is_peak_window) {
      return "Active Peak Window (18:00–22:00)";
    }
    const currentHour = currentStep.hour;
    if (currentHour < 18) {
      const diffHours = 18 - currentHour;
      const h = Math.floor(diffHours);
      const m = Math.round((diffHours - h) * 60);
      return `peak window in ${h}h ${m}m`;
    }
    return "Off-peak window";
  }, [currentStep.hour, currentStep.is_peak_window]);

  // Waveform load bars (last 24 steps up to current)
  const recentLoadBars = useMemo(() => {
    const bars: number[] = [];
    const startIdx = Math.max(0, currentStepIndex - 23);
    for (let i = startIdx; i <= currentStepIndex; i++) {
      const stepData = timesteps[i];
      if (stepData) {
        // Normalized percentage of feeder capacity (12 MW)
        const pct = Math.round((stepData.gridnudge_total_load_mw / 12.0) * 100);
        bars.push(pct);
      }
    }
    // Pad to 24 if at beginning of day
    while (bars.length < 24) {
      bars.unshift(35);
    }
    return bars;
  }, [currentStepIndex, timesteps]);

  return (
    <div className="w-full flex flex-col gap-6 pt-1 pb-10">
      {/* Top micro-bar: Time & Date pills, Interactive Replay Scrubber (§4.3, §5.1 L8) */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Power Status Indicator */}
        <button
          type="button"
          aria-label="Grid power telemetry active"
          title="Grid Feeder Live Telemetry Active"
          className="w-10 h-10 rounded-full bg-navy-800/90 border border-slate-700/60 flex items-center justify-center text-slate-300 hover:text-white transition shadow-sm"
        >
          <Zap className="w-4 h-4 text-nudge-gold" />
        </button>

        {/* Current Sim Clock Chip */}
        <div className="px-5 py-2 rounded-full bg-navy-800/90 border border-slate-700/60 font-mono text-sm font-bold text-white tracking-wider shadow-sm flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>{formattedTime} IST</span>
        </div>

        {/* Simulated Date Chip */}
        <div className="px-5 py-2 rounded-full bg-navy-800/90 border border-slate-700/60 text-sm font-medium text-slate-200 shadow-sm">
          Sat, 10 Oct · Sim
        </div>

        {/* Live Replay Scrubber and Controls (§4.3) */}
        <div className="flex-1 min-w-[320px] flex items-center gap-3 px-4 py-1.5 rounded-full bg-navy-900/80 border border-slate-800/70 shadow-md">
          {/* Play / Pause button */}
          <button
            type="button"
            onClick={() => setIsPlaying(!isPlaying)}
            aria-label={isPlaying ? "Pause simulation replay" : "Play simulation replay"}
            className="w-7 h-7 rounded-full bg-nudge-gold text-navy-950 flex items-center justify-center hover:bg-yellow-300 transition font-bold"
          >
            {isPlaying ? (
              <Pause className="w-3.5 h-3.5 fill-current" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
            )}
          </button>

          {/* Speed Toggle (1x, 4x, 16x) */}
          <button
            type="button"
            onClick={() => {
              if (playbackSpeed === 1) setPlaybackSpeed(4);
              else if (playbackSpeed === 4) setPlaybackSpeed(16);
              else setPlaybackSpeed(1);
            }}
            className="px-2 py-0.5 rounded-md bg-navy-800 hover:bg-navy-700 text-[10px] font-mono font-bold text-amber-300 border border-slate-700 transition"
            title="Toggle playback speed (1×, 4×, 16×)"
          >
            {playbackSpeed}×
          </button>

          {/* Timeline Range Slider */}
          <span className="text-[11px] font-mono text-slate-400 shrink-0">
            Step {currentStepIndex}/95
          </span>

          <input
            type="range"
            min={0}
            max={timesteps.length - 1 || 95}
            value={currentStepIndex}
            onChange={(e) => setCurrentStepIndex(Number(e.target.value))}
            aria-label="Simulation timeline scrubber"
            className="flex-1 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-nudge-gold"
          />

          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
              currentStep.is_peak_window
                ? "bg-orange-500/20 text-orange-300 border border-orange-500/30"
                : "bg-slate-800 text-slate-400"
            }`}
          >
            {currentStep.is_peak_window ? "PEAK (18:00–22:00)" : "OFF-PEAK"}
          </span>

          {/* Quick jump buttons */}
          <div className="hidden xl:flex items-center gap-1.5 pl-2 border-l border-slate-800">
            <button
              type="button"
              onClick={jumpToPeak}
              className="px-2 py-0.5 rounded text-[10px] bg-navy-800 hover:bg-navy-700 text-slate-300 hover:text-white transition"
              title="Jump to peak evening window (18:45)"
            >
              Peak
            </button>
            <button
              type="button"
              onClick={jumpToVeto}
              className="px-2 py-0.5 rounded text-[10px] bg-navy-800 hover:bg-navy-700 text-sky-300 hover:text-white transition"
              title="Jump to first safety veto (19:15)"
            >
              First Veto
            </button>
            <button
              type="button"
              onClick={jumpToEvent}
              className="px-2 py-0.5 rounded text-[10px] bg-navy-800 hover:bg-navy-700 text-orange-300 hover:text-white transition"
              title="Jump to heatwave event start (14:00)"
            >
              Event
            </button>
          </div>
        </div>
      </div>

      {/* Main 3-Column Layout (Desktop 1440x900 hero per spec §5.1) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (Width 3/12 / 340px) */}
        <div className="lg:col-span-3 flex flex-col gap-4">
          {/* Module L5: Fleet Load Card */}
          <FleetLoadCard
            currentMw={currentMw}
            timeToPeak={timeToPeakText}
            loadBars={recentLoadBars}
            onClick={() => setHeroView(heroView === "ring" ? "timeline" : "ring")}
          />

          {/* Module L6: Confidence Rings */}
          <ConfidenceRings journeyPct={94} chargingPct={91} />

          {/* Module L7: Attention Budget Bar */}
          <AttentionBudget
            usedPct={62}
            shadowPrice={shadowPrice}
            rule="8% of plugged-in EVs per interval"
          />

          {/* Run & Mode Selector Dropdown (§4.2) */}
          <div className="relative mt-1">
            <button
              type="button"
              onClick={() => setIsScenarioDropdownOpen(!isScenarioDropdownOpen)}
              className="w-full flex items-center justify-between p-2.5 rounded-full bg-navy-800/90 border border-slate-700/60 hover:border-slate-500 transition group shadow-md"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-orange-600 text-white font-bold text-xs flex items-center justify-center shadow-sm">
                  VS
                </div>
                <div className="flex flex-col text-left">
                  <span className="text-xs font-semibold text-slate-100">
                    {mode} · {scenario}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    Delhi 2,000 EVs · Seed 42
                  </span>
                </div>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-400 group-hover:text-white mr-2" />
            </button>

            {isScenarioDropdownOpen && (
              <div className="absolute left-0 right-0 top-full mt-2 rounded-2xl bg-navy-900/95 border border-slate-700 shadow-2xl backdrop-blur-md overflow-hidden z-30 p-2 space-y-1">
                <div className="px-3 py-1 text-[10px] uppercase font-mono text-slate-400 border-b border-slate-800">
                  Execution Mode
                </div>
                <div className="grid grid-cols-3 gap-1 p-1">
                  {(["Replay", "Live", "Fixtures"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setMode(m)}
                      className={`py-1 text-xs rounded-lg font-medium transition ${
                        mode === m
                          ? "bg-amber-500/20 text-nudge-gold font-bold"
                          : "text-slate-400 hover:bg-white/5 hover:text-white"
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>

                <div className="px-3 py-1 text-[10px] uppercase font-mono text-slate-400 border-b border-slate-800 mt-2">
                  Stress Scenario Track
                </div>
                {[
                  { name: "Heatwave", event: "heatwave" as EventType },
                  { name: "Solar Drop", event: "solar_drop" as EventType },
                  { name: "Station Outage", event: "station_outage" as EventType },
                  { name: "Tariff Hike", event: "tariff_change" as EventType },
                ].map((sc) => (
                  <button
                    key={sc.name}
                    type="button"
                    onClick={() => {
                      handleSelectEvent(sc.event);
                      setIsScenarioDropdownOpen(false);
                    }}
                    className={`w-full px-3 py-2 text-left text-xs rounded-xl flex items-center justify-between transition ${
                      scenario === sc.name
                        ? "bg-amber-500/20 text-nudge-gold font-bold"
                        : "text-slate-300 hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <span>{sc.name}</span>
                    {scenario === sc.name && (
                      <span className="text-[10px] font-mono text-amber-400">ACTIVE</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Center Column: Hero Grid Ring / Timeline (§5.1 Module L1, Width 6/12) */}
        <div className="lg:col-span-6 flex flex-col items-center justify-center pt-1">
          {/* Top Controls: Feeder Zone Pill & Ring/Timeline Toggle */}
          <div className="w-full flex items-center justify-between gap-3 mb-4 px-2">
            {/* Feeder Zone Pill */}
            <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-navy-800/90 border border-slate-700/60 shadow-md">
              <span className="w-2.5 h-2.5 rounded-full bg-orange-500 animate-pulse" />
              <span className="text-xs sm:text-sm font-semibold text-slate-100">
                Feeder zone 7 · Delhi Substation
              </span>
            </div>

            {/* View Switcher: Ring | Timeline Toggle per spec §5.1 L1 */}
            <div className="flex items-center p-1 rounded-full bg-navy-900/80 border border-slate-700/60 shadow-md">
              <button
                type="button"
                onClick={() => setHeroView("ring")}
                aria-label="Concentric Gauge Ring view"
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition ${
                  heroView === "ring"
                    ? "bg-[#253952] text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <PieChart className="w-3.5 h-3.5" />
                <span>Ring</span>
              </button>

              <button
                type="button"
                onClick={() => setHeroView("timeline")}
                aria-label="24h Timeline Chart view"
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition ${
                  heroView === "timeline"
                    ? "bg-[#253952] text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5" />
                <span>Timeline</span>
              </button>
            </div>
          </div>

          {/* Centerpiece Hero Container: Ring OR Timeline */}
          <div className="w-full min-h-[380px] flex items-center justify-center my-2 p-2 rounded-3xl glass-panel relative border border-slate-700/50">
            {/* Expand Full Modal Icon Button */}
            <button
              type="button"
              onClick={() => setShowFullChart(true)}
              aria-label="Expand full screen load modal"
              title="Expand full screen load chart modal"
              className="absolute top-3 right-3 w-8 h-8 rounded-full bg-navy-900/80 border border-slate-700/60 hover:border-slate-500 flex items-center justify-center text-slate-400 hover:text-white transition z-20"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>

            {heroView === "ring" ? (
              <div className="py-2">
                <ConcentricGauge
                  broadcastPct={broadcastPct}
                  gridnudgePct={gridnudgePct}
                  capacityMw={12.0}
                  isolatedSeries={isolatedSeries}
                />
              </div>
            ) : (
              <div className="w-full py-2">
                <InlineTimelineChart
                  timesteps={timesteps}
                  currentStepIndex={currentStepIndex}
                  onStepSelect={(step) => setCurrentStepIndex(step)}
                  activeEvent={activeEvent}
                />
              </div>
            )}
          </div>

          {/* Sub-legend pills below gauge (§5.1 L1: Click to isolate) */}
          <div className="flex flex-wrap items-center justify-center gap-3 mt-4 mb-6">
            <button
              type="button"
              onClick={() =>
                setIsolatedSeries(isolatedSeries === "broadcast" ? "all" : "broadcast")
              }
              title="Click to isolate Broadcast Baseline"
              className={`flex items-center gap-2 px-4 py-2 rounded-full border transition shadow-md cursor-pointer ${
                isolatedSeries === "broadcast"
                  ? "bg-orange-600/30 border-orange-500 ring-2 ring-orange-500/50"
                  : "bg-navy-800/90 border-slate-700/60 hover:border-orange-400"
              }`}
            >
              <span className="w-3 h-3 rounded-full bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.6)]" />
              <span className="text-xs sm:text-sm font-medium text-slate-200">
                Broadcast {broadcastPct}%
              </span>
              {broadcastPct > 100 && (
                <span className="text-[10px] font-mono text-red-400 font-bold">
                  (+{broadcastPct - 100}% OVERSHOOT)
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() =>
                setIsolatedSeries(isolatedSeries === "gridnudge" ? "all" : "gridnudge")
              }
              title="Click to isolate GridNudge load"
              className={`flex items-center gap-2 px-4 py-2 rounded-full border transition shadow-md cursor-pointer ${
                isolatedSeries === "gridnudge"
                  ? "bg-yellow-500/30 border-amber-400 ring-2 ring-yellow-400/50"
                  : "bg-navy-800/90 border-slate-700/60 hover:border-nudge-gold"
              }`}
            >
              <span className="w-3 h-3 rounded-full bg-nudge-gold shadow-[0_0_8px_rgba(250,204,21,0.6)]" />
              <span className="text-xs sm:text-sm font-semibold text-white">
                GridNudge {gridnudgePct}%
              </span>
              <span className="text-[10px] font-mono text-emerald-400 font-bold">
                (SAFE)
              </span>
            </button>

            {isolatedSeries !== "all" && (
              <button
                type="button"
                onClick={() => setIsolatedSeries("all")}
                className="text-[11px] text-slate-400 hover:text-white underline ml-1"
              >
                Reset
              </button>
            )}
          </div>

          {/* Floating Dock Controls (§4.6) */}
          <FloatingDock
            isPlaying={isPlaying}
            onTogglePlay={() => setIsPlaying(!isPlaying)}
            isTimelineView={heroView === "timeline"}
            onToggleTimelineView={() =>
              setHeroView(heroView === "ring" ? "timeline" : "ring")
            }
            onJumpToPeak={jumpToPeak}
          />
        </div>

        {/* Right Column (Width 3/12 / 340px) */}
        <div className="lg:col-span-3 flex flex-col gap-5">
          {/* Module L2: Hero Circular Peak Reduction Orb */}
          <PeakReductionCircle seedCount={10} />

          {/* Module L3: Metrics Summary Card */}
          <MetricsSummary
            nudgesPerUser={0.8}
            broadcastNudges={4.0}
            vetoedCount={37}
            silentPct={71}
            strandedCount={0}
          />

          {/* Module L4: Event Injector */}
          <div className="my-1">
            <EventInjector
              activeEvent={activeEvent}
              onSelectEvent={handleSelectEvent}
            />
          </div>

          {/* Module L9: Safety Veto Alert bottom right ticker */}
          <div className="mt-1">
            <SafetyVetoAlert
              userId="u_2310"
              condition="journey_conf_lb 0.82 < 0.90"
              decisionId="d_002_safety_veto"
            />
          </div>
        </div>
      </div>

      {/* Module L10: Live Decision Ticker Strip (§5.1 L10) */}
      <div className="mt-2">
        <LiveDecisionTicker />
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
