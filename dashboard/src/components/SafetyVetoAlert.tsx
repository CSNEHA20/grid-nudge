"use client";

import Link from "next/link";
import { ShieldCheck } from "lucide-react";

interface SafetyVetoAlertProps {
  userId?: string;
  condition?: string;
  decisionId?: string;
}

export function SafetyVetoAlert({
  userId = "u_2310",
  condition = "journey_conf_lb 0.82 < 0.90",
  decisionId = "d_002_safety_veto",
}: SafetyVetoAlertProps) {
  return (
    <Link
      href={`/decision/${decisionId}`}
      className="flex items-center justify-between gap-4 px-4 py-2.5 rounded-full bg-navy-800/90 border border-slate-700/60 hover:border-sky-400/60 transition group shadow-md"
    >
      <div className="flex flex-col text-left">
        <span className="text-sm font-semibold text-slate-100 group-hover:text-sky-300 transition">
          {userId} vetoed
        </span>
        <span className="text-[11px] font-mono text-slate-400">
          {condition}
        </span>
      </div>

      <div className="w-9 h-9 rounded-full bg-[#1e2f47] text-sky-400 flex items-center justify-center group-hover:bg-sky-500 group-hover:text-white transition shadow-sm">
        <ShieldCheck className="w-5 h-5" />
      </div>
    </Link>
  );
}
