"use client";

import Link from "next/link";
import {
  Sparkles,
  Calendar,
  LayoutGrid,
  TrendingUp,
  SlidersHorizontal,
  Play,
  Pause,
  Layers,
  Zap,
  Car,
  ListFilter,
  ShieldAlert,
} from "lucide-react";

interface FloatingDockProps {
  isPlaying?: boolean;
  onTogglePlay?: () => void;
  isTimelineView?: boolean;
  onToggleTimelineView?: () => void;
  onJumpToPeak?: () => void;
  latestVetoId?: string;
  latestVetoReason?: string;
}

export function FloatingDock({
  isPlaying = false,
  onTogglePlay,
  isTimelineView = false,
  onToggleTimelineView,
  onJumpToPeak,
  latestVetoId = "d_002_safety_veto",
  latestVetoReason = "u_2310 vetoed · journey_conf_lb 0.82 < 0.90",
}: FloatingDockProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-2 rounded-full bg-navy-800/90 border border-slate-700/60 backdrop-blur-md shadow-2xl select-none max-w-full">
      {/* Left Mode / Play Controls */}
      <div className="flex items-center gap-1.5">
        {onTogglePlay && (
          <button
            type="button"
            onClick={onTogglePlay}
            aria-label={isPlaying ? "Pause simulation replay" : "Play simulation replay"}
            title={isPlaying ? "Pause simulation replay (Space)" : "Play simulation replay (Space)"}
            className="w-9 h-9 rounded-full bg-nudge-gold text-navy-950 flex items-center justify-center hover:bg-yellow-300 transition shadow-sm font-bold"
          >
            {isPlaying ? (
              <Pause className="w-3.5 h-3.5 fill-current" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
            )}
          </button>
        )}

        {/* Quick Jump to Peak */}
        {onJumpToPeak && (
          <button
            type="button"
            onClick={onJumpToPeak}
            aria-label="Jump to peak window (18:45)"
            title="Quick jump to peak window (18:45)"
            className="w-9 h-9 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
          >
            <Calendar className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Toggle Ring vs 24h Timeline */}
        {onToggleTimelineView && (
          <button
            type="button"
            onClick={onToggleTimelineView}
            aria-label={isTimelineView ? "Switch to Concentric Gauge Ring" : "Switch to 24h Timeline Chart"}
            title={isTimelineView ? "Switch to Radial Gauge View" : "Toggle 24-Hour Timeline Load Chart"}
            className={`w-9 h-9 rounded-full flex items-center justify-center transition ${
              isTimelineView
                ? "bg-amber-500 text-navy-950 font-bold shadow-md"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Center Nav Icons */}
      <div className="flex items-center gap-1">
        {/* Decisions Browser */}
        <Link
          href="/decisions"
          aria-label="Decisions Browser"
          title="Decision Browser: Search, Filter & Audit"
          className="w-9 h-9 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
        >
          <ListFilter className="w-3.5 h-3.5" />
        </Link>

        {/* Evaluation / Proof Insights */}
        <Link
          href="/evaluation"
          aria-label="Insights & Evaluation"
          title="Evaluation: Proof, Scoreboard & Calibration"
          className="w-9 h-9 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
        >
          <Sparkles className="w-3.5 h-3.5" />
        </Link>

        {/* Main Mission Control Live (Center Hero, larger button) */}
        <Link
          href="/live"
          aria-label="Live Mission Control"
          title="Live Mission Control"
          className="w-10 h-10 rounded-full bg-[#273a52] text-nudge-gold border border-nudge-gold/30 flex items-center justify-center shadow-inner hover:scale-105 transition"
        >
          <LayoutGrid className="w-4 h-4" />
        </Link>

        {/* Digital Twin Explorer */}
        <Link
          href="/twin"
          aria-label="Digital Twin Explorer"
          title="Digital Twin Explorer: Fleet, Stations, Grid & Batteries"
          className="w-9 h-9 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
        >
          <Layers className="w-3.5 h-3.5" />
        </Link>

        {/* Flexibility Forecast */}
        <Link
          href="/flexibility"
          aria-label="Flexibility Forecast"
          title="Flexibility Forecast: Physical Envelope vs Adoption"
          className="w-9 h-9 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
        >
          <Zap className="w-3.5 h-3.5" />
        </Link>

        {/* EV Test Drive */}
        <Link
          href="/testdrive"
          aria-label="EV Test Drive"
          title="EV Test Drive: Ownership Confidence & Risk Assessment"
          className="w-9 h-9 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
        >
          <Car className="w-3.5 h-3.5" />
        </Link>

        {/* Settings / Assumptions / About */}
        <Link
          href="/about"
          aria-label="About & Assumptions register"
          title="About, Data Sources & Assumptions Register"
          className="w-9 h-9 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Right Latest Safety Event Chip (§4.6) */}
      <Link
        href={`/decision/${latestVetoId}`}
        aria-label="View latest safety veto decision"
        title="View latest safety veto decision card"
        className="hidden md:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-400/30 text-sm font-mono text-cyan-300 transition"
      >
        <ShieldAlert className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
        <span className="truncate max-w-[210px]">{latestVetoReason}</span>
      </Link>
    </div>
  );
}
