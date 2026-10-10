"use client";

import {
  Sparkles,
  Calendar,
  LayoutGrid,
  TrendingUp,
  Sun,
  Play,
  Pause,
} from "lucide-react";

interface FloatingDockProps {
  isPlaying?: boolean;
  onTogglePlay?: () => void;
  showFullChart?: boolean;
  onToggleFullChart?: () => void;
}

export function FloatingDock({
  isPlaying = false,
  onTogglePlay,
  showFullChart = false,
  onToggleFullChart,
}: FloatingDockProps) {
  return (
    <div className="flex items-center gap-2 p-1.5 rounded-full bg-navy-800/90 border border-slate-700/60 backdrop-blur-md shadow-lg">
      {/* Play/Pause simulator replay */}
      {onTogglePlay && (
        <button
          type="button"
          onClick={onTogglePlay}
          title={isPlaying ? "Pause simulation replay" : "Play simulation replay"}
          className="w-10 h-10 rounded-full bg-nudge-gold text-navy-950 flex items-center justify-center hover:bg-yellow-300 transition shadow-sm font-bold"
        >
          {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
        </button>
      )}

      {/* Sparkles */}
      <button
        type="button"
        title="AI optimization insights"
        className="w-10 h-10 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
      >
        <Sparkles className="w-4 h-4" />
      </button>

      {/* Calendar */}
      <button
        type="button"
        title="Timeline schedule"
        className="w-10 h-10 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
      >
        <Calendar className="w-4 h-4" />
      </button>

      {/* App Grid (active / main view) */}
      <button
        type="button"
        title="Main Feeder View"
        className="w-10 h-10 rounded-full bg-[#273a52] text-white flex items-center justify-center shadow-inner"
      >
        <LayoutGrid className="w-4 h-4" />
      </button>

      {/* Trend Curve (toggle 24h curve) */}
      <button
        type="button"
        onClick={onToggleFullChart}
        title={showFullChart ? "Hide 24h Fleet Load Curve" : "View 24h Fleet Load Curve"}
        className={`w-10 h-10 rounded-full flex items-center justify-center transition ${
          showFullChart
            ? "bg-amber-500 text-navy-950 font-bold"
            : "text-slate-400 hover:text-white hover:bg-white/5"
        }`}
      >
        <TrendingUp className="w-4 h-4" />
      </button>

      {/* Sun / Weather */}
      <button
        type="button"
        title="Weather & Solar generation view"
        className="w-10 h-10 rounded-full text-slate-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition"
      >
        <Sun className="w-4 h-4" />
      </button>
    </div>
  );
}
