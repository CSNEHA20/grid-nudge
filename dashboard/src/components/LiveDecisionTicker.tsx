"use client";

import Link from "next/link";
import { ShieldAlert, CheckCircle2, VolumeX, AlertTriangle } from "lucide-react";

export interface DecisionTickerItem {
  id: string;
  time: string;
  userId: string;
  planType: string;
  frame: string;
  status: "SENT" | "SILENT" | "VETOED" | "FAIL-SILENT";
  summary: string;
}

const DEFAULT_ITEMS: DecisionTickerItem[] = [
  {
    id: "d_001_nudge_cost",
    time: "18:45",
    userId: "user_delhi_0412",
    planType: "delay",
    frame: "cost",
    status: "SENT",
    summary: "Shift to 22:30 · Save ₹51",
  },
  {
    id: "d_002_safety_veto",
    time: "19:15",
    userId: "user_delhi_1088",
    planType: "delay",
    frame: "none",
    status: "VETOED",
    summary: "Safety Veto: journey_conf_lb 0.82 < 0.90",
  },
  {
    id: "d_003_learned_silence",
    time: "19:30",
    userId: "user_delhi_0044",
    planType: "none",
    frame: "none",
    status: "SILENT",
    summary: "Learned silence · uplift ≤ 0 (would shift anyway)",
  },
  {
    id: "d_001_nudge_cost",
    time: "19:45",
    userId: "user_delhi_0711",
    planType: "delay",
    frame: "green",
    status: "SENT",
    summary: "Shift to 23:00 · 84% solar mix",
  },
  {
    id: "d_002_safety_veto",
    time: "20:00",
    userId: "user_delhi_1420",
    planType: "relocate",
    frame: "convenience",
    status: "VETOED",
    summary: "Safety Veto: station queue ETA wait > 25m",
  },
];

interface LiveDecisionTickerProps {
  items?: DecisionTickerItem[];
}

export function LiveDecisionTicker({
  items = DEFAULT_ITEMS,
}: LiveDecisionTickerProps) {
  return (
    <div className="w-full flex items-center gap-3 px-4 py-2 rounded-2xl glass-panel overflow-x-auto scrollbar-none border border-slate-700/60 shadow-md">
      <div className="flex items-center gap-2 pr-3 border-r border-slate-700/70 shrink-0">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-xs uppercase font-mono font-bold text-slate-300 tracking-wider">
          Decision Stream
        </span>
      </div>

      <div className="flex items-center gap-3">
        {items.map((item) => {
          let badgeClass = "bg-slate-700/60 text-slate-300 border-slate-600";
          let icon = <CheckCircle2 className="w-3 h-3 text-emerald-400" />;

          if (item.status === "VETOED") {
            badgeClass = "bg-sky-500/15 text-sky-300 border-sky-500/40";
            icon = <ShieldAlert className="w-3 h-3 text-sky-400" />;
          } else if (item.status === "SILENT") {
            badgeClass = "bg-amber-500/15 text-nudge-gold border-amber-500/30";
            icon = <VolumeX className="w-3 h-3 text-amber-400" />;
          } else if (item.status === "FAIL-SILENT") {
            badgeClass = "bg-red-500/15 text-red-300 border-red-500/40";
            icon = <AlertTriangle className="w-3 h-3 text-red-400" />;
          }

          return (
            <Link
              key={`${item.id}-${item.time}`}
              href={`/decision/${item.id}`}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-navy-900/70 hover:bg-navy-800/90 border border-slate-700/40 hover:border-slate-500 transition shrink-0 group text-xs"
            >
              <span className="font-mono text-slate-400 text-[11px]">{item.time}</span>
              <span className="font-mono font-semibold text-slate-200 group-hover:text-white">
                {item.userId}
              </span>

              <span
                className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-bold border ${badgeClass}`}
              >
                {icon}
                {item.status}
              </span>

              <span className="text-[11px] text-slate-400 group-hover:text-slate-300 truncate max-w-[200px]">
                {item.summary}
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
