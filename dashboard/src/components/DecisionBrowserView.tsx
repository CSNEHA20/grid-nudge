"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  VolumeX,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";
import { DecisionIndexItem } from "@/lib/data";

interface DecisionBrowserViewProps {
  decisions: DecisionIndexItem[];
  initialStatusFilter?: string;
}

export function DecisionBrowserView({
  decisions = [],
  initialStatusFilter,
}: DecisionBrowserViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>(
    initialStatusFilter || "ALL"
  );
  const [planFilter, setPlanFilter] = useState<string>("ALL");
  const [sortField, setSortField] = useState<"sim_time" | "journey_conf_lb" | "uplift_mean">("sim_time");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Summary Metrics
  const summary = useMemo(() => {
    const total = decisions.length;
    const vetoed = decisions.filter((d) => d.status === "VETOED").length;
    const silent = decisions.filter((d) => d.status === "SILENT").length;
    const sent = decisions.filter((d) => d.status === "SENT").length;
    const failSilent = decisions.filter((d) => d.status === "FAIL-SILENT").length;
    const vetoShare = total > 0 ? ((vetoed / total) * 100).toFixed(1) : "0.0";
    const sentNudges = decisions.filter((d) => d.status === "SENT");
    const meanUplift =
      sentNudges.length > 0
        ? (sentNudges.reduce((acc, d) => acc + d.uplift_mean, 0) / sentNudges.length).toFixed(2)
        : "0.00";

    return { total, vetoed, silent, sent, failSilent, vetoShare, meanUplift };
  }, [decisions]);

  // Filtered & Sorted decisions
  const filteredDecisions = useMemo(() => {
    return decisions
      .filter((d) => {
        if (statusFilter !== "ALL" && d.status !== statusFilter) return false;
        if (planFilter !== "ALL" && d.plan_type !== planFilter) return false;
        if (
          searchQuery &&
          !d.user_id.toLowerCase().includes(searchQuery.toLowerCase()) &&
          !d.decision_id.toLowerCase().includes(searchQuery.toLowerCase())
        ) {
          return false;
        }
        return true;
      })
      .sort((a, b) => {
        const valA = a[sortField];
        const valB = b[sortField];
        if (typeof valA === "string") {
          return sortOrder === "asc"
            ? (valA as string).localeCompare(valB as string)
            : (valB as string).localeCompare(valA as string);
        }
        return sortOrder === "asc"
          ? (valA as number) - (valB as number)
          : (valB as number) - (valA as number);
      });
  }, [decisions, statusFilter, planFilter, searchQuery, sortField, sortOrder]);

  const handleSort = (field: "sim_time" | "journey_conf_lb" | "uplift_mean") => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  return (
    <div className="w-full max-w-7xl mx-auto flex flex-col gap-6 pt-2 pb-16">
      {/* Header */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono text-slate-300">
            Audit Log · 2,000 EVs Fleet · Replay Run
          </span>
          <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            SIMULATION
          </span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          Decision Browser
        </h1>
        <p className="text-lg text-slate-200 max-w-3xl leading-relaxed">
          Search, filter, and inspect every intervention decision across the fleet. Audit safety vetoes,
          learned silence states, and persuasion frames.
        </p>
      </div>

      {/* Summary KPI Chips */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="p-3.5 rounded-2xl glass-panel flex flex-col justify-between">
          <span className="text-sm text-slate-300 font-medium">Total Decisions</span>
          <span className="text-2xl font-black text-white">{summary.total}</span>
        </div>
        <div className="p-3.5 rounded-2xl glass-panel flex flex-col justify-between border-l-2 border-l-amber-500">
          <span className="text-sm text-slate-300 font-medium">Nudges Sent</span>
          <span className="text-2xl font-black text-amber-400">{summary.sent}</span>
        </div>
        <div className="p-3.5 rounded-2xl glass-panel flex flex-col justify-between border-l-2 border-l-cyan-400">
          <span className="text-sm text-slate-300 font-medium">Safety Vetoed</span>
          <span className="text-2xl font-black text-cyan-300">{summary.vetoed}</span>
        </div>
        <div className="p-3.5 rounded-2xl glass-panel flex flex-col justify-between border-l-2 border-l-slate-400">
          <span className="text-sm text-slate-300 font-medium">Learned Silence</span>
          <span className="text-2xl font-black text-slate-300">{summary.silent}</span>
        </div>
        <div className="p-3.5 rounded-2xl glass-panel flex flex-col justify-between">
          <span className="text-sm text-slate-300 font-medium">Veto Rate</span>
          <span className="text-2xl font-black text-white">{summary.vetoShare}%</span>
        </div>
        <div className="p-3.5 rounded-2xl glass-panel flex flex-col justify-between">
          <span className="text-sm text-slate-300 font-medium">Mean Uplift (Sent)</span>
          <span className="text-2xl font-black text-nudge-gold">+{summary.meanUplift}</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-3xl glass-panel flex flex-wrap items-center justify-between gap-4">
        {/* Status Filter Chips */}
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { id: "ALL", label: "All Statuses" },
            { id: "SENT", label: "Sent" },
            { id: "VETOED", label: "Safety Vetoed" },
            { id: "SILENT", label: "Learned Silence" },
            { id: "FAIL-SILENT", label: "Fail-Silent" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3.5 py-1.5 rounded-full text-sm font-semibold transition ${
                statusFilter === tab.id
                  ? "bg-amber-500 text-navy-950 shadow-md"
                  : "bg-white/5 text-slate-300 hover:text-white hover:bg-white/10"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Plan Filter & Search Input */}
        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          <select
            value={planFilter}
            onChange={(e) => setPlanFilter(e.target.value)}
            className="px-3 py-2 rounded-xl bg-navy-900 border border-white/15 text-sm text-white focus:outline-none focus:border-amber-400"
          >
            <option value="ALL">All Plan Types</option>
            <option value="delay">delay (home scheduled)</option>
            <option value="relocate">relocate (public solar hub)</option>
            <option value="slow_charge">slow_charge (battery-gentle)</option>
            <option value="top_up_now">top_up_now (urgent plug)</option>
            <option value="none">none (silence)</option>
          </select>

          <div className="relative flex-1 sm:w-60">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-300" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search user or decision ID..."
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-navy-900 border border-white/15 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-amber-400"
            />
          </div>
        </div>
      </div>

      {/* Decisions Data Table */}
      <div className="rounded-3xl glass-panel readable-panel overflow-hidden border border-white/15">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-base">
            <thead className="bg-navy-900/80 text-sm uppercase tracking-wider text-slate-300 border-b border-white/10 select-none">
              <tr>
                <th
                  className="p-4 cursor-pointer hover:text-white"
                  onClick={() => handleSort("sim_time")}
                >
                  Sim Time {sortField === "sim_time" && (sortOrder === "asc" ? "↑" : "↓")}
                </th>
                <th className="p-4">User ID</th>
                <th className="p-4">Status</th>
                <th className="p-4">Plan & Frame</th>
                <th
                  className="p-4 cursor-pointer hover:text-white"
                  onClick={() => handleSort("journey_conf_lb")}
                >
                  Journey Conf LB {sortField === "journey_conf_lb" && (sortOrder === "asc" ? "↑" : "↓")}
                </th>
                <th
                  className="p-4 cursor-pointer hover:text-white"
                  onClick={() => handleSort("uplift_mean")}
                >
                  Uplift (mean) {sortField === "uplift_mean" && (sortOrder === "asc" ? "↑" : "↓")}
                </th>
                <th className="p-4">Propensity</th>
                <th className="p-4">Slot</th>
                <th className="p-4">Outcome</th>
                <th className="p-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredDecisions.length === 0 ? (
                <tr>
                  <td colSpan={10} className="p-8 text-center text-slate-300 text-base">
                    No decisions match these filters. Try resetting search or status filters.
                  </td>
                </tr>
              ) : (
                filteredDecisions.map((d) => {
                  const isVetoed = d.status === "VETOED";
                  const isSilent = d.status === "SILENT";
                  const isFailSilent = d.status === "FAIL-SILENT";
                  const isSent = d.status === "SENT";

                  return (
                    <tr
                      key={d.decision_id}
                      className={`hover:bg-white/5 transition group ${
                        isVetoed ? "bg-cyan-500/5" : ""
                      }`}
                    >
                      <td className="p-4 font-mono text-sm text-slate-300">
                        {d.sim_time.replace("2026-10-10T", "").replace("+05:30", "")}
                      </td>
                      <td className="p-4 font-mono text-sm font-semibold text-white">
                        {d.user_id}
                      </td>
                      <td className="p-4">
                        {isVetoed && (
                          <span className="inline-flex items-center gap-1 text-sm font-bold font-mono px-2.5 py-1 rounded-full bg-cyan-400/15 text-cyan-300 border border-cyan-400/30">
                            <ShieldAlert className="w-3 h-3" />
                            VETOED
                          </span>
                        )}
                        {isSilent && (
                          <span className="inline-flex items-center gap-1 text-sm font-bold font-mono px-2.5 py-1 rounded-full bg-slate-700/60 text-slate-300 border border-slate-600/50">
                            <VolumeX className="w-3 h-3" />
                            SILENT
                          </span>
                        )}
                        {isFailSilent && (
                          <span className="inline-flex items-center gap-1 text-sm font-bold font-mono px-2.5 py-1 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30">
                            <AlertTriangle className="w-3 h-3" />
                            FAIL-SILENT
                          </span>
                        )}
                        {isSent && (
                          <span className="inline-flex items-center gap-1 text-sm font-bold font-mono px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                            <CheckCircle2 className="w-3 h-3" />
                            SENT
                          </span>
                        )}
                      </td>
                      <td className="p-4">
                        <div className="flex flex-col">
                          <span className="font-semibold text-sm text-white capitalize">
                            {d.plan_type}
                          </span>
                          <span className="text-sm text-slate-300">
                            frame: {d.frame}
                          </span>
                        </div>
                      </td>
                      <td className="p-4 font-mono text-sm">
                        <span
                          className={
                            d.journey_conf_lb < 0.90
                              ? "text-rose-400 font-bold"
                              : "text-emerald-400 font-medium"
                          }
                        >
                          {(d.journey_conf_lb * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="p-4 font-mono text-sm">
                        <span
                          className={
                            d.uplift_mean > 0
                              ? "text-amber-300 font-semibold"
                              : "text-slate-300"
                          }
                        >
                          {d.uplift_mean > 0 ? `+${d.uplift_mean}` : d.uplift_mean}
                        </span>
                      </td>
                      <td className="p-4 font-mono text-sm text-slate-300">
                        {(d.propensity * 100).toFixed(0)}%
                      </td>
                      <td className="p-4 font-mono text-sm text-slate-300">
                        {d.slot || "—"}
                      </td>
                      <td className="p-4">
                        <span className="text-sm uppercase font-mono px-2 py-0.5 rounded bg-white/5 text-slate-300">
                          {d.outcome}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <Link
                          href={`/decision/${d.decision_id}`}
                          className="inline-flex items-center gap-1 text-sm font-semibold text-amber-400 hover:text-amber-300 transition"
                        >
                          Audit Card
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
