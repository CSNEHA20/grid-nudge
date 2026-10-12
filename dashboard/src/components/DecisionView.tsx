"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  ShieldAlert,
  Sparkles,
  Info,
} from "lucide-react";
import { DecisionRecord } from "@/types/decision-record";

interface DecisionViewProps {
  decisions: DecisionRecord[];
  initialId?: string;
}

export function DecisionView({ decisions = [], initialId }: DecisionViewProps) {
  const defaultId = initialId || "d_002_safety_veto";
  const [selectedId, setSelectedId] = useState<string>(
    decisions.find((d) => d.decision_id === defaultId)?.decision_id ||
      decisions[0]?.decision_id ||
      "d_002_safety_veto"
  );
  const [showExplanation, setShowExplanation] = useState<boolean>(false);

  const currentDecision =
    decisions.find((d) => d.decision_id === selectedId) || decisions[0];

  const isVetoed =
    currentDecision?.safety?.cedar === "DENY" ||
    (currentDecision?.safety?.vetoed && currentDecision.safety.vetoed.length > 0);
  const isFailSilent = Boolean(currentDecision?.fail_silent);
  const isSilence =
    currentDecision?.persuasion?.frame === "none" && !isVetoed && !isFailSilent;

  const vetoReason =
    currentDecision?.safety?.vetoed && currentDecision.safety.vetoed.length > 0
      ? currentDecision.safety.vetoed[0]
      : "p1: journey_conf_lb 0.82 < 0.90 (mandatory 90% threshold breached)";

  // Facts used chips
  const factsUsed = currentDecision?.language?.facts_used || {
    plan_start: "22:30",
    savings_inr: 38,
    target_soc: "80%",
    departure_time: "06:30",
  };

  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col gap-6 pt-2 pb-16">
      {/* Top Breadcrumb & Selector Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link
          href="/live"
          className="inline-flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Live Fleet Overview
        </Link>

        {/* Quick Decision Switcher Pills */}
        <div className="flex flex-wrap items-center gap-2 bg-navy-800/80 p-1 rounded-full border border-slate-700/60">
          {decisions.map((d) => {
            const isCurrent = d.decision_id === selectedId;
            const label =
              d.decision_id === "d_002_safety_veto"
                ? "d_002 (Safety Veto)"
                : d.decision_id === "d_001_nudge_cost"
                ? "d_001 (Safe Shift)"
                : d.decision_id === "d_003_learned_silence"
                ? "d_003 (Learned Silence)"
                : d.decision_id === "d_004_fail_silent"
                ? "d_004 (Fail-Silent)"
                : d.decision_id;

            return (
              <button
                key={d.decision_id}
                type="button"
                onClick={() => setSelectedId(d.decision_id)}
                className={`px-3 py-1.5 rounded-full text-sm font-mono transition ${
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
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-slate-400">
              Decision {currentDecision.decision_id} · {currentDecision.user_id} ·{" "}
              {currentDecision.sim_time.replace("2026-10-10T", "").slice(0, 5)} sim
            </span>
            {isVetoed && (
              <span className="text-sm font-bold font-mono px-2.5 py-0.5 rounded-full bg-cyan-400/15 text-cyan-300 border border-cyan-400/30">
                SAFETY VETO
              </span>
            )}
            {isSilence && (
              <span className="text-sm font-bold font-mono px-2.5 py-0.5 rounded-full bg-slate-700 text-slate-300 border border-slate-600">
                LEARNED SILENCE
              </span>
            )}
            {isFailSilent && (
              <span className="text-sm font-bold font-mono px-2.5 py-0.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30">
                FAIL-SILENT (SAFE DEFAULT)
              </span>
            )}
            {!isVetoed && !isSilence && !isFailSilent && (
              <span className="text-sm font-bold font-mono px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                NUDGE APPROVED & SENT
              </span>
            )}
          </div>

          {/* Explain Button (§5.2) */}
          <button
            type="button"
            onClick={() => setShowExplanation(!showExplanation)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/15 text-sm text-amber-300 font-medium transition"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Explain Decision</span>
          </button>
        </div>

        <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-white">
          {isVetoed
            ? "Why the cheaper plan was blocked."
            : isSilence
            ? "Why no nudge was sent (Learned Silence)."
            : isFailSilent
            ? "Safe default applied: no nudge sent (Fail-Silent)."
            : "Safe delay plan approved with cost frame."}
        </h1>

        <p className="text-base text-slate-300 max-w-3xl leading-relaxed">
          {isVetoed
            ? "Delaying charging saves money but risks tomorrow's 06:30 morning trip. Safety invariants and Cedar removed it before the contextual bandit ever saw it."
            : isSilence
            ? "The contextual bandit estimated an uplift of zero (user charges off-peak routinely anyway). Attention budget was saved to prevent habituation."
            : isFailSilent
            ? "Cedar evaluation timed out (50ms limit). In accordance with AGENTS.md Rule 1.3 Fail-Silent, the system gracefully degraded to silence."
            : "Journey confidence exceeds the mandatory 90% threshold for tomorrow morning. Shifted to overnight green window with ₹38 estimated user saving."}
        </p>

        {showExplanation && (
          <div className="p-4 rounded-2xl bg-navy-900/90 border border-amber-500/30 text-sm text-slate-200 mt-2 space-y-2 animate-in fade-in">
            <div className="font-bold text-amber-400 uppercase tracking-wide flex items-center gap-1.5">
              <Info className="w-4 h-4" />
              Auditable Pipeline Explanation (Pure Structured Facts)
            </div>
            <p>
              1. <strong>Perception:</strong> Evaluated journey to arrival SOC reserve under ambient heatwave conditions.
            </p>
            <p>
              2. <strong>Safety Invariants:</strong> Lower bound confidence calculated. Threshold rule:{" "}
              <code className="text-amber-300">journey_conf_lb &gt;= 0.90</code>.
            </p>
            <p>
              3. <strong>Cedar Gate:</strong> Cedar policy engine evaluated Principal (User), Action (SendNudge), and Resource. Verdict:{" "}
              <code className="text-amber-300">{currentDecision.safety?.cedar}</code>.
            </p>
            <p>
              4. <strong>LinTS Bandit:</strong> Evaluated extra behavior change (uplift) and chose action{" "}
              <code className="text-amber-300">{currentDecision.persuasion?.frame}</code>.
            </p>
          </div>
        )}
      </div>

      {/* 6-Card Pipeline Stepper Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mt-2">
        {/* Card 1: 1 · PERCEPTION */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[300px]">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm uppercase tracking-wider font-semibold text-slate-400">
                1 · Perception
              </span>
              <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Calibrated
              </span>
            </div>

            <div className="mt-3 flex items-baseline gap-2">
              <span
                className={`text-5xl sm:text-6xl font-black tracking-tight ${
                  (currentDecision.journey?.p_arrive_above_reserve || 0.82) < 0.9
                    ? "text-rose-400"
                    : "text-amber-400"
                }`}
              >
                {Math.round((currentDecision.journey?.p_arrive_above_reserve || 0.82) * 100)}%
              </span>
              <span className="text-sm text-slate-400 font-mono">
                P(arrival SOC &ge; 10%)
              </span>
            </div>

            {/* Mini SOC Trajectory Chart representation */}
            <div className="mt-4 p-3 rounded-2xl bg-black/30 border border-white/5 space-y-2">
              <div className="flex items-center justify-between text-sm text-slate-300">
                <span>SOC Trajectory vs Reserve</span>
                <span className="font-mono text-amber-300">Target 90%</span>
              </div>
              <div className="relative h-4 w-full bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="absolute left-0 top-0 bottom-0 bg-rose-500/40 border-r-2 border-rose-400"
                  style={{ width: "10%" }}
                  title="Reserve buffer: 10%"
                />
                <div
                  className="absolute left-0 top-0 bottom-0 bg-amber-400/80 rounded-full"
                  style={{
                    width: `${Math.round(
                      (currentDecision.journey?.arrival_soc_q50 || 0.36) * 100
                    )}%`,
                  }}
                  title="Predicted arrival SOC q50"
                />
              </div>
              <div className="flex justify-between text-xs font-mono text-slate-400">
                <span>0%</span>
                <span className="text-rose-300">10% (Reserve Line)</span>
                <span>q50: {Math.round((currentDecision.journey?.arrival_soc_q50 || 0.36) * 100)}%</span>
                <span>100%</span>
              </div>
            </div>
          </div>

          <div className="space-y-1 pt-3 text-sm font-mono text-slate-300 border-t border-slate-700/50">
            <div>
              Arrival SOC:{" "}
              {currentDecision.journey
                ? `${Math.round(currentDecision.journey.arrival_soc_q10 * 100)}% (q10) / ${Math.round(
                    currentDecision.journey.arrival_soc_q50 * 100
                  )}% (q50) / ${Math.round(currentDecision.journey.arrival_soc_q90 * 100)}% (q90)`
                : "6% / 14% / 22%"}
            </div>
            <div>
              Battery Stress: {currentDecision.battery?.stress_score ?? 0.28} · SoH delta:{" "}
              {currentDecision.battery?.soh_delta_range_pct
                ? `[${currentDecision.battery.soh_delta_range_pct[0]}%, +${currentDecision.battery.soh_delta_range_pct[1]}%]`
                : "[-0.01%, +0.04%]"}
            </div>
            <div>
              Station Wait ETA:{" "}
              {currentDecision.station?.eta_wait_min_q50 ?? 0}m -{" "}
              {currentDecision.station?.eta_wait_min_q90 ?? 0}m (Reliability:{" "}
              {(currentDecision.station?.reliability ?? 0.98) * 100}%)
            </div>
          </div>
        </div>

        {/* Card 2: 2 · CANDIDATE PLANS */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[300px]">
          <div>
            <span className="text-sm uppercase tracking-wider font-semibold text-slate-400">
              2 · Candidate plans
            </span>

            <div className="mt-3 space-y-2.5">
              {currentDecision.plans && currentDecision.plans.length > 0 ? (
                currentDecision.plans.map((p) => {
                  const outcomes = (p.outcomes || {}) as Record<string, number>;
                  const isPlanVetoed =
                    typeof outcomes.journey_conf_lb === "number" &&
                    outcomes.journey_conf_lb < 0.90;
                  const isPlanChosen =
                    currentDecision.persuasion?.chosen_plan === p.plan_id;

                  return (
                    <div
                      key={p.plan_id}
                      className={`p-2.5 rounded-xl border transition ${
                        isPlanVetoed
                          ? "bg-cyan-500/10 border-cyan-400/40 text-cyan-200"
                          : isPlanChosen
                          ? "bg-amber-500/15 border-amber-500/40 text-white"
                          : "bg-navy-900/60 border-white/10 text-slate-200"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold font-mono">
                          {p.plan_id} · {p.type}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-bold ${
                            isPlanVetoed
                              ? "bg-cyan-400/20 text-cyan-300"
                              : isPlanChosen
                              ? "bg-amber-400/20 text-amber-300"
                              : "bg-emerald-500/20 text-emerald-300"
                          }`}
                        >
                          {isPlanVetoed ? "VETOED" : isPlanChosen ? "CHOSEN" : "SAFE"}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center justify-between text-sm font-mono text-slate-400">
                        <span>
                          Cost: ₹{outcomes.cost_inr !== undefined ? outcomes.cost_inr.toFixed(0) : "—"}
                        </span>
                        <span>
                          Conf LB:{" "}
                          <strong
                            className={
                              isPlanVetoed ? "text-cyan-300" : "text-emerald-300"
                            }
                          >
                            {outcomes.journey_conf_lb !== undefined
                              ? `${(outcomes.journey_conf_lb * 100).toFixed(0)}%`
                              : "—"}
                          </strong>
                        </span>
                        <span>
                          Grid: {outcomes.grid_value !== undefined ? outcomes.grid_value.toFixed(1) : "0.0"}
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-sm text-slate-400 p-4">No candidate plans generated.</div>
              )}
            </div>
          </div>

          <div className="pt-3 text-sm text-slate-400 border-t border-slate-700/50">
            Plans evaluated under physics simulator prior to persuasion bandit.
          </div>
        </div>

        {/* Card 3: 3 · SAFETY GATE (Visually Dominant) */}
        <div
          className={`p-6 rounded-3xl flex flex-col justify-between min-h-[300px] transition shadow-xl ${
            isVetoed
              ? "bg-[#1d354b]/90 border-2 border-cyan-400/80 shadow-cyan-500/10"
              : isFailSilent
              ? "bg-[#331f28]/90 border-2 border-rose-500/60"
              : "glass-panel"
          }`}
        >
          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm uppercase tracking-wider font-bold text-cyan-300">
                3 · Safety gate
              </span>
              <ShieldAlert className="w-4 h-4 text-cyan-400" />
            </div>

            {/* Inset veto or verdict reason box */}
            <div className="mt-3 p-3 rounded-xl bg-navy-950/90 border border-cyan-500/30 text-sm font-mono text-cyan-200 break-words">
              {isVetoed ? (
                <>
                  <div className="text-xs text-cyan-400 uppercase font-bold mb-1">
                    [SAFETY VETO ENGAGED]
                  </div>
                  {vetoReason}
                </>
              ) : isFailSilent ? (
                <>
                  <div className="text-xs text-rose-400 uppercase font-bold mb-1">
                    [FAIL-SILENT TRIGGERED]
                  </div>
                  {currentDecision.error || "Execution fault; safe default: no nudge sent."}
                </>
              ) : (
                <>
                  <div className="text-xs text-emerald-400 uppercase font-bold mb-1">
                    [ALL INVARIANTS PASS]
                  </div>
                  Journey confidence lower bound &ge; 90% reserve.
                </>
              )}
            </div>

            <div className="mt-4 space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-300 font-medium">Physical Invariants</span>
                <span className="font-bold text-nudge-yellow">
                  {currentDecision.safety?.invariants_ok ? "PASS" : "FAIL"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-300 font-medium">Cedar Policy Verdict</span>
                <span
                  className={`font-bold font-mono ${
                    currentDecision.safety?.cedar === "ALLOW"
                      ? "text-emerald-400"
                      : currentDecision.safety?.cedar === "DENY"
                      ? "text-cyan-300"
                      : "text-rose-400"
                  }`}
                >
                  {currentDecision.safety?.cedar || "ALLOW"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-300 font-medium">Nudges Today / Cap</span>
                <span className="font-mono text-white">1 / 3</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-300 font-medium">Quiet Hours (23:00–06:00)</span>
                <span className="font-mono text-slate-300">No</span>
              </div>
            </div>
          </div>

          <div className="pt-3 text-sm text-slate-400 border-t border-slate-700/50 flex items-center justify-between">
            <span>Rule: journey_conf_lb &ge; 0.90</span>
            <Link href="/about#policies" className="text-cyan-300 hover:underline">
              View Cedar Rules
            </Link>
          </div>
        </div>

        {/* Card 4: 4 · PERSUASION */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[300px]">
          <div>
            <span className="text-sm uppercase tracking-wider font-semibold text-slate-400">
              4 · Persuasion
            </span>

            <div className="mt-3">
              <h3 className="text-xl font-bold text-white tracking-tight capitalize">
                {currentDecision.persuasion?.frame === "none"
                  ? "none (Learned Silence)"
                  : `${currentDecision.persuasion?.frame || "cost"} frame`}
              </h3>
              <p className="text-sm text-slate-400 mt-0.5">
                Timing: {currentDecision.persuasion?.timing || "at_plug_in"}
              </p>
            </div>

            <div className="mt-4 space-y-2 text-sm text-slate-300 font-mono">
              <div className="p-2.5 rounded-xl bg-navy-900/60 border border-white/5 space-y-1">
                <div className="flex justify-between">
                  <span>Expected Uplift:</span>
                  <span className="font-bold text-amber-300">
                    {currentDecision.persuasion?.uplift_mean !== undefined
                      ? `${currentDecision.persuasion.uplift_mean > 0 ? "+" : ""}${currentDecision.persuasion.uplift_mean.toFixed(2)} kWh`
                      : "+0.11 kWh"}
                  </span>
                </div>
                <div className="flex justify-between text-sm text-slate-400">
                  <span>Uplift p10:</span>
                  <span>
                    {currentDecision.persuasion?.uplift_p10 !== undefined
                      ? `${currentDecision.persuasion.uplift_p10.toFixed(2)} kWh`
                      : "+0.03 kWh"}
                  </span>
                </div>
              </div>

              <div className="flex justify-between pt-1">
                <span className="text-slate-400">Action Propensity:</span>
                <span className="text-white font-bold">
                  {((currentDecision.persuasion?.propensity ?? 0.76) * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Bandit Exploration:</span>
                <span className="text-slate-300">
                  {currentDecision.persuasion?.explored ? "True (Randomized)" : "False (Greedy Posterior)"}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-3 text-sm text-slate-400 border-t border-slate-700/50">
            Linear Thompson Sampling with first-class none arm.
          </div>
        </div>

        {/* Card 5: 5 · ALLOCATION */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[300px]">
          <div>
            <span className="text-sm uppercase tracking-wider font-semibold text-slate-400">
              5 · Allocation
            </span>

            <div className="mt-3">
              <span className="text-5xl font-black text-white tracking-tight">
                {currentDecision.allocation?.slot || "22:15"}
              </span>
              <p className="text-base text-slate-300 font-medium mt-1">
                staggered charging slot
              </p>
            </div>

            <div className="mt-4 p-3 rounded-2xl bg-navy-900/60 border border-white/5 space-y-1.5 text-sm font-mono">
              <div className="flex justify-between text-slate-300">
                <span>Shadow Price:</span>
                <span className="text-amber-300">
                  ₹{currentDecision.allocation?.shadow_price?.toFixed(2) || "0.31"}/kWh
                </span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Selected by Allocator:</span>
                <span
                  className={
                    currentDecision.allocation?.selected
                      ? "text-emerald-400 font-bold"
                      : "text-slate-400"
                  }
                >
                  {currentDecision.allocation?.selected ? "YES" : "NO"}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-3 text-sm text-slate-400 border-t border-slate-700/50">
            Anti-herding staggering prevents rebound peak on Delhi Zone 7 feeder.
          </div>
        </div>

        {/* Card 6: 6 · MESSAGE & VERIFICATION */}
        <div className="p-6 rounded-3xl glass-panel flex flex-col justify-between min-h-[300px]">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm uppercase tracking-wider font-semibold text-slate-400">
                6 · Message & Verification
              </span>
              <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Numbers Verified
              </span>
            </div>

            {/* White speech bubble */}
            <div className="mt-3 p-4 rounded-2xl bg-white text-navy-950 shadow-xl font-medium text-base leading-relaxed">
              {currentDecision.language?.message ? (
                `“${currentDecision.language.message}”`
              ) : isVetoed ? (
                <span className="text-slate-400 italic">
                  [No message generated: safety invariant vetoed plan before communication stage]
                </span>
              ) : isSilence ? (
                <span className="text-slate-400 italic">
                  [No message generated: bandit chose &apos;none&apos; arm (learned silence)]
                </span>
              ) : isFailSilent ? (
                <span className="text-slate-400 italic">
                  [No message generated: fail-silent safe default applied]
                </span>
              ) : (
                "“Charging a little slower tonight protects your battery and still reaches 80% by 06:30. Saves ₹12.”"
              )}
            </div>

            {/* Facts Used Chips (§5.2) */}
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <span className="text-xs uppercase font-mono text-slate-400">
                Facts payload:
              </span>
              {Object.entries(factsUsed).map(([k, v]) => (
                <span
                  key={k}
                  className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-xs font-mono text-amber-300"
                >
                  {k}: {String(v)}
                </span>
              ))}
            </div>
          </div>

          <div className="pt-3 flex items-center justify-between text-sm text-slate-400 border-t border-slate-700/50">
            <span className="font-mono">
              Source: {currentDecision.language?.source || "template"} · LLM never decides
            </span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
        </div>
      </div>

      {/* Outcome Footer & Related Decisions Strip (§5.2) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
        {/* Outcome Card */}
        <div className="p-5 rounded-3xl glass-panel flex flex-col justify-between">
          <span className="text-sm uppercase tracking-wider font-semibold text-slate-400">
            Observed Outcome & Causal Reward
          </span>
          <div className="grid grid-cols-4 gap-2 mt-3 text-center">
            <div className="p-3 rounded-2xl bg-navy-900/60 border border-white/5">
              <span className="text-xs uppercase text-slate-400 block">Adopted</span>
              <span className="text-base font-bold text-white">
                {currentDecision.outcome?.adopted === null
                  ? "—"
                  : currentDecision.outcome?.adopted
                  ? "Yes"
                  : "No"}
              </span>
            </div>
            <div className="p-3 rounded-2xl bg-navy-900/60 border border-white/5">
              <span className="text-xs uppercase text-slate-400 block">Shifted</span>
              <span className="text-base font-bold text-amber-300">
                {currentDecision.outcome?.kwh_shifted?.toFixed(1) || "0.0"} kWh
              </span>
            </div>
            <div className="p-3 rounded-2xl bg-navy-900/60 border border-white/5">
              <span className="text-xs uppercase text-slate-400 block">Savings</span>
              <span className="text-base font-bold text-white">
                ₹{currentDecision.outcome?.adopted ? "38" : "0"}
              </span>
            </div>
            <div className="p-3 rounded-2xl bg-navy-900/60 border border-white/5">
              <span className="text-xs uppercase text-slate-400 block">Reward</span>
              <span className="text-base font-bold text-emerald-400">
                {currentDecision.outcome?.reward?.toFixed(1) || "0.0"}
              </span>
            </div>
          </div>
        </div>

        {/* User Fatigue History */}
        <div className="p-5 rounded-3xl glass-panel flex flex-col justify-between">
          <span className="text-sm uppercase tracking-wider font-semibold text-slate-400">
            User Fatigue History & Habituation State
          </span>
          <div className="flex items-center justify-between gap-4 mt-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-navy-900/80 border border-white/10 flex items-center justify-center font-mono font-bold text-amber-300 text-lg">
                0.24
              </div>
              <div>
                <span className="text-sm font-semibold text-white block">
                  Fatigue Index (Half-life 3 days)
                </span>
                <span className="text-sm text-slate-400">
                  Last nudge sent: 2 days ago · Cap remaining: 2
                </span>
              </div>
            </div>
            <span className="text-sm font-mono px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
              Low Fatigue
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
