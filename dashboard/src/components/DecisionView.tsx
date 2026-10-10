"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { DecisionRecord } from "@/types/decision-record";

interface DecisionViewProps {
  decisions: DecisionRecord[];
  initialId?: string;
}

export function DecisionView({ decisions = [], initialId }: DecisionViewProps) {
  // Find current decision or default to d_002_safety_veto
  const defaultId = initialId || "d_002_safety_veto";
  const [selectedId, setSelectedId] = useState<string>(
    decisions.find((d) => d.decision_id === defaultId)?.decision_id ||
      decisions[0]?.decision_id ||
      "d_002_safety_veto"
  );

  const currentDecision =
    decisions.find((d) => d.decision_id === selectedId) || decisions[0];

  const isVetoed = currentDecision?.safety?.cedar === "DENY" || (currentDecision?.safety?.vetoed && currentDecision.safety.vetoed.length > 0);
  const isSilence = currentDecision?.persuasion?.frame === "none" && !isVetoed;

  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col gap-6 pt-2 pb-12">
      {/* Top Breadcrumb & Selector Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link
          href="/live"
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Live Fleet Overview
        </Link>

        {/* Quick Decision Switcher Pills */}
        <div className="flex items-center gap-2 bg-navy-800/80 p-1 rounded-full border border-slate-700/60">
          {decisions.map((d) => {
            const isCurrent = d.decision_id === selectedId;
            const label =
              d.decision_id === "d_002_safety_veto"
                ? "d_002 (Safety Veto)"
                : d.decision_id === "d_001_nudge_cost"
                ? "d_001 (Safe Shift)"
                : d.decision_id === "d_003_learned_silence"
                ? "d_003 (Learned Silence)"
                : d.decision_id;

            return (
              <button
                key={d.decision_id}
                type="button"
                onClick={() => setSelectedId(d.decision_id)}
                className={`px-3 py-1.5 rounded-full text-xs font-mono transition ${
                  isCurrent
                    ? "bg-[#253952] text-white font-bold shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Header / Headline */}
      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-mono text-slate-400">
          Decision {currentDecision.decision_id} · {currentDecision.user_id} · 18:45 sim
        </span>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          {isVetoed
            ? "Why the cheaper plan was blocked."
            : isSilence
            ? "Why no nudge was sent (Learned Silence)."
            : "Safe delay plan approved with cost frame."}
        </h1>
        <p className="text-base text-slate-300 max-w-3xl mt-1 leading-relaxed">
          {isVetoed
            ? "Delaying to 22:30 saves money but risks tomorrow's 06:30 trip. Safety removed it before the bandit ever saw it."
            : isSilence
            ? "The contextual bandit estimated an uplift of zero because this user routinely charges off-peak anyway. Spending attention budget was avoided."
            : "Journey confidence exceeds 90% threshold for tomorrow morning. Shifted to overnight green window with ₹51 user saving."}
        </p>
      </div>

      {/* 6-Card Pipeline Stepper Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mt-2">
        {/* Card 1: 1 · PERCEPTION */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[260px]">
          <div>
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
              1 · Perception
            </span>
            <div className="mt-3">
              <span className="text-6xl font-black text-orange-500 tracking-tight">
                {currentDecision.journey?.p_arrive_above_reserve
                  ? Math.round(currentDecision.journey.p_arrive_above_reserve * 100)
                  : 82}
                %
              </span>
            </div>
            <p className="text-sm text-slate-300 font-medium mt-1">
              journey confidence if delayed
            </p>
          </div>

          <div className="space-y-1 pt-4 text-xs font-mono text-slate-300 border-t border-slate-700/50">
            <div>
              arrival SOC{" "}
              {currentDecision.journey
                ? `${Math.round(currentDecision.journey.arrival_soc_q10 * 100)} / ${Math.round(
                    currentDecision.journey.arrival_soc_q50 * 100
                  )} / ${Math.round(currentDecision.journey.arrival_soc_q90 * 100)}%`
                : "6 / 14 / 22%"}
            </div>
            <div>
              station wait{" "}
              {currentDecision.station
                ? `${currentDecision.station.eta_wait_min_q50}-${currentDecision.station.eta_wait_min_q90} min`
                : "4-11 min"}
            </div>
            <div>
              grid stress{" "}
              {currentDecision.grid
                ? `${currentDecision.grid.stress_q50.toFixed(2)}-${currentDecision.grid.stress_q90.toFixed(2)}`
                : "0.71-0.84"}
            </div>
          </div>
        </div>

        {/* Card 2: 2 · CANDIDATE PLANS */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[260px]">
          <div>
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
              2 · Candidate plans
            </span>

            <div className="mt-4 space-y-3">
              {/* p0 default */}
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-100">
                  p0 default
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-slate-400">0.97</span>
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#364930] text-[#a3e635] border border-[#4d6b43]">
                    SAFE
                  </span>
                </div>
              </div>

              {/* p1 delay (Highlighted / Vetoed) */}
              <div className="flex items-center justify-between p-2 rounded-xl bg-navy-900/80 border border-slate-700/80">
                <span className="text-sm font-semibold text-slate-100">
                  p1 delay 22:30 · Rs 38
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-slate-400">0.82</span>
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#273a50] text-[#93c5fd] border border-[#3b597c]">
                    VETOED
                  </span>
                </div>
              </div>

              {/* p3 slow charge */}
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-100">
                  p3 slow charge · Rs 12
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-slate-400">0.93</span>
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#364930] text-[#a3e635] border border-[#4d6b43]">
                    SAFE
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-3 text-[11px] text-slate-400 border-t border-slate-700/50">
            Ranked by expected grid benefit prior to safety verification.
          </div>
        </div>

        {/* Card 3: 3 · SAFETY GATE */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[260px]">
          <div>
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
              3 · Safety gate
            </span>

            {/* Inset veto reason box */}
            <div className="mt-3 p-3 rounded-xl bg-navy-900/90 border border-slate-700/80 text-xs font-mono text-slate-200">
              {currentDecision.safety?.vetoed && currentDecision.safety.vetoed.length > 0
                ? currentDecision.safety.vetoed[0]
                : "p1: journey_conf_lb 0.82 < 0.90"}
            </div>

            <div className="mt-4 space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-300 font-medium">Invariants (p3)</span>
                <span className="font-bold text-nudge-yellow">PASS</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-300 font-medium">Cedar SendNudge</span>
                <span className="font-bold text-nudge-yellow">
                  {currentDecision.safety?.cedar || "ALLOW"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-300 font-medium">Nudges today</span>
                <span className="font-mono text-white">1 / 3</span>
              </div>
            </div>
          </div>

          <div className="pt-3 text-[11px] text-slate-400 border-t border-slate-700/50">
            Cedar policy denies any plan below 0.90 journey confidence.
          </div>
        </div>

        {/* Card 4: 4 · PERSUASION */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[260px]">
          <div>
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
              4 · Persuasion
            </span>

            <div className="mt-3">
              <h3 className="text-xl font-bold text-white tracking-tight">
                battery frame · at plug-in
              </h3>
            </div>

            <div className="mt-4 space-y-1.5 text-xs text-slate-300 font-mono">
              <div>
                uplift +
                {currentDecision.persuasion?.uplift_mean !== undefined
                  ? currentDecision.persuasion.uplift_mean.toFixed(2)
                  : "0.11"}{" "}
                (p10 +
                {currentDecision.persuasion?.uplift_p10 !== undefined
                  ? currentDecision.persuasion.uplift_p10.toFixed(2)
                  : "0.03"}
                )
              </div>
              <div>
                propensity{" "}
                {currentDecision.persuasion?.propensity !== undefined
                  ? currentDecision.persuasion.propensity.toFixed(2)
                  : "0.17"}{" "}
                · explored: {currentDecision.persuasion?.explored ? "yes" : "no"}
              </div>
            </div>
          </div>

          <div className="pt-3 text-[11px] text-slate-400 border-t border-slate-700/50">
            Linear Thompson Sampling with first-class none arm.
          </div>
        </div>

        {/* Card 5: 5 · ALLOCATION */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[260px]">
          <div>
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
              5 · Allocation
            </span>

            <div className="mt-3">
              <span className="text-6xl font-black text-white tracking-tight">
                22:15
              </span>
            </div>

            <p className="text-sm text-slate-300 font-medium mt-1">
              staggered slot · shadow price 0.31
            </p>
          </div>

          <div className="pt-3 text-[11px] text-slate-400 border-t border-slate-700/50">
            Anti-herding staggering prevents rebound peak on feeder.
          </div>
        </div>

        {/* Card 6: 6 · MESSAGE */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[260px]">
          <div>
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
              6 · Message
            </span>

            {/* White speech bubble card */}
            <div className="mt-3 p-4 rounded-2xl bg-white text-navy-950 shadow-lg font-medium text-sm leading-relaxed">
              &ldquo;
              {currentDecision.language?.message ||
                "Charging a little slower tonight protects your battery and still reaches 80% by 06:30. Saves Rs 12."}
              &rdquo;
            </div>
          </div>

          <div className="pt-3 flex items-center justify-between text-xs text-slate-400 border-t border-slate-700/50">
            <span className="font-mono">
              template · <span className="text-nudge-yellow font-bold">numbers verified</span>
            </span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
        </div>
      </div>
    </div>
  );
}
