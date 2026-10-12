"use client";

import { useState } from "react";
import {
  ShieldCheck,
  Sliders,
  Search,
  Layers,
  Cloud,
} from "lucide-react";
import { AssumptionItem, SourceItem, PolicyRuleItem } from "@/lib/data";

interface AboutViewProps {
  assumptions: AssumptionItem[];
  sources: SourceItem[];
  policies: PolicyRuleItem[];
}

export function AboutView({
  assumptions = [],
  sources = [],
  policies = [],
}: AboutViewProps) {
  const [activeTab, setActiveTab] = useState<"real_vs_sim" | "sources" | "assumptions" | "policies" | "architecture">("real_vs_sim");
  const [assumptionSearch, setAssumptionSearch] = useState("");

  const filteredAssumptions = assumptions.filter(
    (a) =>
      a.parameter.toLowerCase().includes(assumptionSearch.toLowerCase()) ||
      a.category.toLowerCase().includes(assumptionSearch.toLowerCase()) ||
      a.assumed_value.toLowerCase().includes(assumptionSearch.toLowerCase())
  );

  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col gap-6 pt-2 pb-16">
      {/* Header */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono text-slate-400">
            Transparency Register · Full Auditability
          </span>
          <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            AGENTS.md Rule 1.1 Honesty
          </span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          Assumptions, Data & Architecture
        </h1>
        <p className="text-base text-slate-300 max-w-3xl leading-relaxed">
          GridNudge never invents benchmark numbers or user behavior. This register explicitly states
          what is real, what is grounded in public datasets, and what is simulated.
        </p>
      </div>

      {/* Tabs Row */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 rounded-full bg-navy-800/90 border border-slate-700/60 max-w-fit">
        {[
          { id: "real_vs_sim", label: "Real vs. Simulated" },
          { id: "sources", label: "Data Sources & Grounding" },
          { id: "assumptions", label: "Assumptions Register" },
          { id: "policies", label: "Cedar Rules (Plain Language)" },
          { id: "architecture", label: "Architecture & AWS" },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id as "real_vs_sim" | "sources" | "assumptions" | "policies" | "architecture")}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition ${
              activeTab === tab.id
                ? "bg-amber-500 text-navy-950 shadow-md"
                : "text-slate-300 hover:text-white hover:bg-white/5"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Real vs Simulated Table */}
      {activeTab === "real_vs_sim" && (
        <div className="p-6 sm:p-8 rounded-3xl glass-panel space-y-6">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Honest Data Hierarchy: Real vs. Simulated
            </h2>
            <p className="text-sm text-slate-300 mt-1">
              Per AGENTS.md Rule 1.1 and Rule 8, we distinguish observed ground truth from synthetic assumptions.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Real Column */}
            <div className="p-5 rounded-2xl bg-emerald-950/30 border border-emerald-500/30 space-y-3">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-base uppercase">
                <ShieldCheck className="w-4 h-4" />
                What is Real in GridNudge
              </div>
              <ul className="text-sm text-slate-200 space-y-2.5 list-disc list-inside">
                <li>
                  <strong>Decision Pipeline Architecture:</strong> Strict separation of Physics Planner, Dual Safety Gates, and LinTS Persuasion Bandit.
                </li>
                <li>
                  <strong>Cedar Authorization Engine:</strong> Automated policy evaluations enforcing quiet hours, cap limits, and journey thresholds.
                </li>
                <li>
                  <strong>Causal Learning Loop:</strong> LinTS contextual bandit posterior updates on verified simulation outcomes.
                </li>
                <li>
                  <strong>AWS Serverless Infrastructure:</strong> Lambda, API Gateway, DynamoDB, SQS FIFO, and S3 IaC SAM deployment.
                </li>
                <li>
                  <strong>Grounding Datasets:</strong> Delhi substation hourly load series (IEEE DataPort), Caltech ACN workplace sessions, and Bailey et al. RCT trials.
                </li>
              </ul>
            </div>

            {/* Simulated Column */}
            <div className="p-5 rounded-2xl bg-amber-950/30 border border-amber-500/30 space-y-3">
              <div className="flex items-center gap-2 text-amber-400 font-bold text-base uppercase">
                <Sliders className="w-4 h-4" />
                What is Simulated / Assumed
              </div>
              <ul className="text-sm text-slate-200 space-y-2.5 list-disc list-inside">
                <li>
                  <strong>Indian EV User Charging Sessions:</strong> Synthesized because granular Indian session-level telematic data is not publicly published.
                </li>
                <li>
                  <strong>Driver Nudge Response:</strong> Grounded in Canadian/Australian RCT trials with Indian cost sensitivity priors; simulated responses.
                </li>
                <li>
                  <strong>Station Reliability & Downtime:</strong> Simulated MTBF (7 days) and MTTR (4 hrs) per connector based on field reports.
                </li>
                <li>
                  <strong>Battery Aging Extrapolation:</strong> Cell lab degradation models provide relative cycle differences; absolute lifespan predictions are forbidden.
                </li>
                <li>
                  <strong>Substation Feeder Limit:</strong> Parameterized 12.0 MW distribution threshold for suburban Delhi feeder zone 7.
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Data Sources List */}
      {activeTab === "sources" && (
        <div className="p-6 sm:p-8 rounded-3xl glass-panel space-y-6">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Data Sources Register (docs/engineering/03_DATASETS.md)
            </h2>
            <p className="text-sm text-slate-300 mt-1">
              Public datasets utilized to ground simulation parameters, vehicle physics, and grid load curves.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sources.map((src, i) => (
              <div
                key={i}
                className="p-4 rounded-2xl bg-navy-900/60 border border-white/10 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-base font-bold text-white">{src.name}</span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-white/5 text-amber-300 border border-white/10">
                      {src.tier}
                    </span>
                  </div>
                  <span className="text-sm font-mono text-slate-400 block mt-0.5">
                    Category: {src.category}
                  </span>
                  <p className="text-sm text-slate-300 mt-2 leading-relaxed">
                    {src.description}
                  </p>
                </div>
                <div className="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between text-sm font-mono text-slate-400">
                  <span>Usage: {src.usage_in_gridnudge}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Assumptions Register */}
      {activeTab === "assumptions" && (
        <div className="p-6 sm:p-8 rounded-3xl glass-panel space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                Assumptions Register (data/ASSUMPTIONS.md)
              </h2>
              <p className="text-sm text-slate-300 mt-1">
                Every synthetic or assumed parameter, rationale, and grounding methodology.
              </p>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                value={assumptionSearch}
                onChange={(e) => setAssumptionSearch(e.target.value)}
                placeholder="Search parameter..."
                className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-navy-900 border border-white/15 text-sm text-white placeholder:text-slate-400 focus:outline-none focus:border-amber-400"
              />
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-white/10">
            <table className="w-full text-left text-sm">
              <thead className="bg-navy-900/80 text-sm uppercase tracking-wider text-slate-400 border-b border-white/10">
                <tr>
                  <th className="p-3.5">Category</th>
                  <th className="p-3.5">Parameter</th>
                  <th className="p-3.5">Assumed Value / Model</th>
                  <th className="p-3.5">Rationale</th>
                  <th className="p-3.5">How to Ground with Real Data</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 font-sans">
                {filteredAssumptions.map((a, i) => (
                  <tr key={i} className="hover:bg-white/5 transition">
                    <td className="p-3.5 font-mono text-amber-300 whitespace-nowrap">
                      {a.category}
                    </td>
                    <td className="p-3.5 font-semibold text-white whitespace-nowrap">
                      {a.parameter}
                    </td>
                    <td className="p-3.5 text-slate-300 font-mono text-sm">
                      {a.assumed_value}
                    </td>
                    <td className="p-3.5 text-slate-300 leading-relaxed min-w-[200px]">
                      {a.rationale}
                    </td>
                    <td className="p-3.5 text-slate-400 text-sm min-w-[180px]">
                      {a.grounding_method}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 4: Cedar Policies */}
      {activeTab === "policies" && (
        <div className="p-6 sm:p-8 rounded-3xl glass-panel space-y-6" id="policies">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Safety Gate Policy in Plain Language (AWS Cedar)
            </h2>
            <p className="text-sm text-slate-300 mt-1">
              Declarative security and safety policies evaluated before any persuasion nudge is authorized.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {policies.map((p) => (
              <div
                key={p.id}
                className="p-5 rounded-2xl bg-navy-900/60 border border-white/10 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-base font-bold text-cyan-300 font-mono">
                      {p.name}
                    </span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                      {p.category}
                    </span>
                  </div>
                  <p className="text-sm text-white mt-2 leading-relaxed">
                    {p.plain_language}
                  </p>
                </div>
                <div className="mt-3 pt-2.5 border-t border-white/5">
                  <span className="text-xs uppercase font-mono text-slate-400 block mb-1">
                    Formal Cedar Statement:
                  </span>
                  <pre className="p-2.5 rounded bg-black/40 text-xs font-mono text-emerald-400 whitespace-pre-wrap">
                    {p.cedar_statement}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 5: Architecture & AWS Map */}
      {activeTab === "architecture" && (
        <div className="p-6 sm:p-8 rounded-3xl glass-panel space-y-6">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Spine Architecture & AWS Serverless Deployment Map
            </h2>
            <p className="text-sm text-slate-300 mt-1">
              Plan → Persuade → Learn closed loop and AWS cloud infrastructure.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* The Spine Architecture */}
            <div className="p-5 rounded-2xl bg-navy-900/60 border border-white/10 space-y-4">
              <div className="flex items-center gap-2 text-amber-400 font-bold text-base uppercase">
                <Layers className="w-4 h-4" />
                The Golden Architecture Spine
              </div>
              <div className="space-y-2 text-sm font-mono">
                {[
                  "1. Digital Twin (2,000 EVs, Delhi Zone 7 Feeder, Weather, Shocks)",
                  "2. Perception (Calibrated Journey Conf, Battery Stress, Wait ETA)",
                  "3. Planner (Enumerate Feasible Charging Plans)",
                  "4. Safety Filter #1 (Remove Unsafe Plans Before Bandit)",
                  "5. LinTS Contextual Bandit (First-class None Arm, Frame Selection)",
                  "6. Allocator (Anti-Herding Staggering, Budget Cap)",
                  "7. Safety Filter #2 (Cedar Policy Verdict Verification)",
                  "8. Language & Facts Verifier (Template / Bedrock Guardrail)",
                  "9. Simulated Driver Response & Causal Reward",
                  "10. Closed-Loop Posterior Policy Update",
                ].map((step, idx) => (
                  <div
                    key={idx}
                    className="p-2 rounded bg-white/5 border border-white/5 text-slate-200"
                  >
                    {step}
                  </div>
                ))}
              </div>
            </div>

            {/* AWS Cloud Architecture */}
            <div className="p-5 rounded-2xl bg-navy-900/60 border border-white/10 space-y-4">
              <div className="flex items-center gap-2 text-cyan-400 font-bold text-base uppercase">
                <Cloud className="w-4 h-4" />
                AWS Serverless Implementation (AWS SAM)
              </div>
              <div className="space-y-3 text-sm text-slate-300 leading-relaxed">
                <div className="p-3 rounded-xl bg-black/30 border border-white/5 space-y-1">
                  <div className="font-bold text-white">API Gateway & Lambda Decide:</div>
                  <p className="text-sm text-slate-400">
                    Exposes <code>POST /decide</code> invoking the pure local pipeline packaged as a thin Lambda adapter.
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-black/30 border border-white/5 space-y-1">
                  <div className="font-bold text-white">DynamoDB On-Demand:</div>
                  <p className="text-sm text-slate-400">
                    Stores DecisionRecords, active user fatigue states, and bandit posterior matrices.
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-black/30 border border-white/5 space-y-1">
                  <div className="font-bold text-white">SQS FIFO & Reward Update:</div>
                  <p className="text-sm text-slate-400">
                    Guarantees single-writer LinTS posterior matrix updates with <code>ReservedConcurrentExecutions = 1</code>.
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-black/30 border border-white/5 space-y-1">
                  <div className="font-bold text-white">S3 Telemetry Lake & CloudWatch:</div>
                  <p className="text-sm text-slate-400">
                    Stores timestamped replay trajectories and logs safety veto counters.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Build Info Card */}
      <div className="p-5 rounded-3xl glass-panel flex flex-wrap items-center justify-between gap-4 text-sm font-mono border border-white/10">
        <div>
          Build: <strong className="text-white">v2.0.0-release</strong> · Commit:{" "}
          <strong className="text-white">git-sha-7c9f82</strong> · Build Date:{" "}
          <strong className="text-slate-300">Oct 11, 2026</strong>
        </div>
        <div className="text-slate-400">
          WeMakeDevs &times; AWS Hackathon · Track: Waste & Energy &rarr; EV Nudges
        </div>
      </div>
    </div>
  );
}
