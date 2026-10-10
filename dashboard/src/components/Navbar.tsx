"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Zap, Bell } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();

  const isLive = pathname === "/" || pathname === "/live";
  const isDecisions = pathname.startsWith("/decision");
  const isEvaluation = pathname === "/evaluation";

  return (
    <header className="relative z-50 w-full px-6 py-4 flex items-center justify-between">
      {/* Brand Logo */}
      <Link href="/live" className="flex items-center gap-3 group">
        <div className="relative w-11 h-11 flex items-center justify-center">
          {/* Hexagon SVG background */}
          <svg
            viewBox="0 0 100 100"
            className="w-full h-full text-navy-800 drop-shadow-md stroke-slate-700/60 transition group-hover:stroke-nudge-gold/60"
            fill="currentColor"
            strokeWidth="3"
          >
            <polygon points="50 3, 93 25, 93 75, 50 97, 7 75, 7 25" />
          </svg>
          <Zap className="absolute w-5 h-5 text-nudge-gold fill-nudge-gold/80 transition transform group-hover:scale-110" />
        </div>
        <div className="hidden sm:block">
          <span className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
            GridNudge
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              v2.0
            </span>
          </span>
        </div>
      </Link>

      {/* Segmented Navigation Tabs */}
      <nav className="flex items-center p-1 rounded-full bg-navy-800/90 border border-slate-700/50 backdrop-blur-md shadow-lg">
        <Link
          href="/live"
          className={`px-6 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
            isLive
              ? "bg-[#253952] text-white shadow-md font-semibold"
              : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
          }`}
        >
          Live
        </Link>
        <Link
          href="/decisions"
          className={`px-6 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
            isDecisions
              ? "bg-[#253952] text-white shadow-md font-semibold"
              : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
          }`}
        >
          Decisions
        </Link>
        <Link
          href="/evaluation"
          className={`px-6 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
            isEvaluation
              ? "bg-[#253952] text-white shadow-md font-semibold"
              : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
          }`}
        >
          Evaluation
        </Link>
      </nav>

      {/* Simulation status & notifications */}
      <div className="flex items-center gap-3">
        <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-full bg-navy-800/80 border border-slate-700/50 backdrop-blur-md text-xs font-mono tracking-wider text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>SIMULATION · SAMPLE DATA</span>
        </div>

        <button
          type="button"
          aria-label="System notifications"
          className="relative w-10 h-10 rounded-full bg-navy-800/80 border border-slate-700/50 hover:border-slate-500 flex items-center justify-center text-slate-300 hover:text-white transition shadow-sm"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-amber-400 ring-2 ring-navy-900" />
        </button>
      </div>
    </header>
  );
}
