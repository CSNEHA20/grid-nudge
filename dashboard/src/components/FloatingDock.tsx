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
} from "lucide-react";

interface FloatingDockProps {
  isPlaying?: boolean;
  onTogglePlay?: () => void;
  isTimelineView?: boolean;
  onToggleTimelineView?: () => void;
  onJumpToPeak?: () => void;
}

export function FloatingDock({
  isPlaying = false,
  onTogglePlay,
  isTimelineView = false,
  onToggleTimelineView,
  onJumpToPeak,
}: FloatingDockProps) {
  return (
    <div className="flex items-center gap-2 p-1.5 rounded-full bg-navy-800/90 border border-slate-700/60 backdrop-blur-md shadow-2xl select-none">
      {/* Play/Pause simulator replay */}
      {onTogglePlay && (
        <button
          type="button"
          onClick={onTogglePlay}
          aria-label={isPlaying ? "Pause simulation replay" : "Play simulation replay"}
          title={isPlaying ? "Pause simulation replay (Space)" : "Play simulation replay (Space)"}
          className="w-10 h-10 rounded-full bg-nudge-gold text-navy-950 flex items-center justify-center hover:bg-yellow-300 transition shadow-sm font-bold"
        >
          {isPlaying ? (
            <Pause className="w-4 h-4 fill-current" />
          ) : (
            <Play className="w-4 h-4 fill-current ml-0.5" />
          )}
        </button>
      )}

      {/* Evaluation / Proof Insights */}
      <Link
        href="/evaluation"
        aria-label="Insights & Evaluation"
        title="Evaluation: Proof, Scoreboard & Calibration"
        className="w-10 h-10 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
      >
        <Sparkles className="w-4 h-4" />
      </Link>

      {/* Quick Jump to Peak */}
      <button
        type="button"
        onClick={onJumpToPeak}
        aria-label="Jump to peak window (18:45)"
        title="Quick jump to peak window (18:45)"
        className="w-10 h-10 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
      >
        <Calendar className="w-4 h-4" />
      </button>

      {/* Main Mission Control Live (Center Hero, larger button) */}
      <Link
        href="/live"
        aria-label="Live Mission Control"
        title="Live Mission Control"
        className="w-11 h-11 rounded-full bg-[#273a52] text-nudge-gold border border-nudge-gold/30 flex items-center justify-center shadow-inner hover:scale-105 transition"
      >
        <LayoutGrid className="w-5 h-5" />
      </Link>

      {/* Toggle Ring vs 24h Timeline */}
      <button
        type="button"
        onClick={onToggleTimelineView}
        aria-label={isTimelineView ? "Switch to Concentric Gauge Ring" : "Switch to 24h Timeline Chart"}
        title={isTimelineView ? "Switch to Radial Gauge View" : "Toggle 24-Hour Timeline Load Chart"}
        className={`w-10 h-10 rounded-full flex items-center justify-center transition ${
          isTimelineView
            ? "bg-amber-500 text-navy-950 font-bold shadow-md"
            : "text-slate-400 hover:text-white hover:bg-white/5"
        }`}
      >
        <TrendingUp className="w-4 h-4" />
      </button>

      {/* Settings / Assumptions / About */}
      <Link
        href="/about"
        aria-label="About & Assumptions register"
        title="About, Data Sources & Assumptions Register"
        className="w-10 h-10 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
      >
        <SlidersHorizontal className="w-4 h-4" />
      </Link>
    </div>
  );
}
