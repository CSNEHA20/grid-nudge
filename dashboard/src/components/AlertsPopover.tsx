"use client";

import Link from "next/link";
import { X, ShieldAlert, AlertTriangle, Clock, Zap, Flame } from "lucide-react";

export interface AlertItem {
  id: string;
  time: string;
  type: "VETO" | "FAIL_SILENT" | "BUDGET" | "STRESS" | "EVENT";
  title: string;
  detail: string;
  link?: string;
}

const DEFAULT_ALERTS: AlertItem[] = [
  {
    id: "alt-1",
    time: "19:15 IST",
    type: "VETO",
    title: "Safety Veto Triggered",
    detail: "u_2310: plan_delay_risky blocked (journey_conf_lb 0.82 < 0.90 threshold)",
    link: "/decision/d_002_safety_veto",
  },
  {
    id: "alt-2",
    time: "18:30 IST",
    type: "STRESS",
    title: "Feeder Stress Spike",
    detail: "Broadcast baseline reached 118% of capacity (14.2 MW / 12.0 MW)",
  },
  {
    id: "alt-3",
    time: "18:45 IST",
    type: "BUDGET",
    title: "Attention Budget Warning",
    detail: "62% interval attention budget utilized (shadow price ₹12.5/nudge)",
  },
  {
    id: "alt-4",
    time: "14:00 IST",
    type: "EVENT",
    title: "Heatwave Stress Injected",
    detail: "+3.5°C temperature rise, 1.25× baseline cooling multiplier active",
  },
];

interface AlertsPopoverProps {
  isOpen: boolean;
  onClose: () => void;
  alerts?: AlertItem[];
}

export function AlertsPopover({
  isOpen,
  onClose,
  alerts = DEFAULT_ALERTS,
}: AlertsPopoverProps) {
  if (!isOpen) return null;

  return (
    <div className="absolute right-0 top-full mt-3 w-80 sm:w-96 rounded-2xl glass-panel p-4 border border-slate-700/80 shadow-2xl z-50 animate-in fade-in zoom-in-95 duration-150">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
          <h4 className="text-sm font-bold text-white tracking-tight">System Alerts</h4>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-navy-800 text-slate-300 border border-slate-700">
            {alerts.length} unread
          </span>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close alerts"
          className="w-7 h-7 rounded-full bg-navy-800/80 hover:bg-navy-700 text-slate-400 hover:text-white flex items-center justify-center transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="mt-3 space-y-2.5 max-h-80 overflow-y-auto pr-1">
        {alerts.map((alert) => {
          let badgeClass = "bg-slate-700/50 text-slate-300 border-slate-600";
          let icon = <Zap className="w-3.5 h-3.5 text-slate-300" />;

          if (alert.type === "VETO") {
            badgeClass = "bg-sky-500/20 text-sky-300 border-sky-500/40";
            icon = <ShieldAlert className="w-3.5 h-3.5 text-sky-400" />;
          } else if (alert.type === "STRESS") {
            badgeClass = "bg-orange-500/20 text-orange-300 border-orange-500/40";
            icon = <AlertTriangle className="w-3.5 h-3.5 text-orange-400" />;
          } else if (alert.type === "BUDGET") {
            badgeClass = "bg-amber-500/20 text-nudge-gold border-amber-500/40";
            icon = <Clock className="w-3.5 h-3.5 text-nudge-gold" />;
          } else if (alert.type === "EVENT") {
            badgeClass = "bg-red-500/20 text-red-300 border-red-500/40";
            icon = <Flame className="w-3.5 h-3.5 text-red-400" />;
          }

          const content = (
            <div className="p-2.5 rounded-xl bg-navy-900/80 hover:bg-navy-800/90 border border-slate-800 hover:border-slate-700 transition flex items-start gap-3 text-left group">
              <div className="mt-0.5 p-1 rounded-lg bg-navy-950 border border-slate-800">
                {icon}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-0.5">
                  <span className="text-xs font-semibold text-white group-hover:text-amber-200 transition truncate">
                    {alert.title}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400 shrink-0">
                    {alert.time}
                  </span>
                </div>

                <p className="text-[11px] text-slate-300 leading-snug line-clamp-2">
                  {alert.detail}
                </p>

                <div className="mt-1.5 flex items-center gap-2">
                  <span
                    className={`text-[9px] uppercase font-mono font-bold px-1.5 py-0.5 rounded border ${badgeClass}`}
                  >
                    {alert.type}
                  </span>
                  {alert.link && (
                    <span className="text-[10px] text-sky-400 group-hover:underline">
                      View details →
                    </span>
                  )}
                </div>
              </div>
            </div>
          );

          return alert.link ? (
            <Link key={alert.id} href={alert.link} onClick={onClose} className="block">
              {content}
            </Link>
          ) : (
            <div key={alert.id}>{content}</div>
          );
        })}
      </div>
    </div>
  );
}
