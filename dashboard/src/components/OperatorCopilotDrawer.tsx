"use client";

import { useState } from "react";
import {
  Sparkles,
  X,
  Send,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { CopilotData } from "@/lib/data";

interface OperatorCopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  copilotData?: CopilotData | null;
}

export function OperatorCopilotDrawer({
  isOpen,
  onClose,
  copilotData,
}: OperatorCopilotDrawerProps) {
  const [messages, setMessages] = useState<
    Array<{
      sender: "user" | "copilot";
      text: string;
      citations?: Array<{ type: string; id: string; label: string }>;
      tools_used?: string[];
      scenario_preview?: {
        title: string;
        events: Array<Record<string, string | number | boolean>>;
        projected_impact: string;
      };
    }>
  >([
    {
      sender: "copilot",
      text: "Hello! I am the GridNudge Operator Copilot. I can inspect and explain any decision, audit safety invariant vetoes, and preview grid disturbance scenarios. What would you like to explore?",
    },
  ]);
  const [inputVal, setInputVal] = useState("");
  const [expandedTools, setExpandedTools] = useState<Record<number, boolean>>({});
  const [injectedScenarios, setInjectedScenarios] = useState<Record<string, boolean>>({});

  if (!isOpen) return null;

  const handleSend = (text: string) => {
    if (!text.trim()) return;

    const userMsg = { sender: "user" as const, text };
    setMessages((prev) => [...prev, userMsg]);
    setInputVal("");

    // Look for a matching answer in copilotData
    const found = copilotData?.conversations?.find((c) =>
      c.question.toLowerCase().includes(text.toLowerCase().slice(0, 15)) ||
      text.toLowerCase().includes(c.question.toLowerCase().slice(0, 15))
    );

    setTimeout(() => {
      if (found) {
        setMessages((prev) => [
          ...prev,
          {
            sender: "copilot",
            text: found.answer,
            citations: found.citations,
            tools_used: found.tools_used,
            scenario_preview: found.scenario_preview,
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            sender: "copilot",
            text: `Auditing telemetry for "${text}". Simulation run metrics: GridNudge (B4) evening peak 20.47 MW (5.6% reduction vs B0), 0 attributable stranded trips, and 100% safety invariant compliance.`,
            citations: [
              { type: "decision", id: "d_001_nudge_cost", label: "Run #42" },
              { type: "rule", id: "cedar_rule_01", label: "Cedar Policy" },
            ],
            tools_used: [
              `search_decision_logs(query='${text.slice(0, 20)}')`,
              "verify_numbers_against_facts()",
            ],
          },
        ]);
      }
    }, 400);
  };

  const toggleTools = (idx: number) => {
    setExpandedTools((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleConfirmScenario = (title: string) => {
    setInjectedScenarios((prev) => ({ ...prev, [title]: true }));
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-navy-950/60 backdrop-blur-sm flex justify-end transition-opacity">
      <div
        className="relative w-full max-w-xl h-full bg-[#18283a]/95 border-l border-white/15 shadow-2xl flex flex-col backdrop-blur-xl animate-in slide-in-from-right duration-300"
        role="dialog"
        aria-modal="true"
        aria-labelledby="copilot-drawer-title"
      >
        {/* Header */}
        <div className="p-5 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2
                id="copilot-drawer-title"
                className="text-lg font-bold text-white flex items-center gap-2"
              >
                Operator Copilot
                <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Read-Only Verified
                </span>
              </h2>
              <p className="text-sm text-slate-400">
                Decision explainability & structured scenario injection
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close Copilot drawer"
            className="w-9 h-9 rounded-full bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white flex items-center justify-center transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Suggested Prompts Strip */}
        {copilotData?.suggested_questions && (
          <div className="p-4 bg-navy-900/40 border-b border-white/5 flex flex-col gap-2">
            <span className="text-sm uppercase font-semibold text-slate-400 tracking-wider">
              Suggested Questions:
            </span>
            <div className="flex flex-wrap gap-2">
              {copilotData.suggested_questions.map((q, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleSend(q)}
                  className="text-sm text-left px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-amber-300 transition"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${
                m.sender === "user" ? "items-end" : "items-start"
              }`}
            >
              <div
                className={`max-w-[88%] rounded-2xl p-4 text-base leading-relaxed ${
                  m.sender === "user"
                    ? "bg-amber-500/20 border border-amber-500/30 text-white"
                    : "bg-navy-800/80 border border-white/10 text-slate-200"
                }`}
              >
                <p>{m.text}</p>

                {/* Citations Chips */}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/10 flex flex-wrap items-center gap-1.5">
                    <span className="text-xs uppercase font-mono text-slate-400 mr-1">
                      Citations:
                    </span>
                    {m.citations.map((c, cIdx) => (
                      <Link
                        key={cIdx}
                        href={
                          c.type === "decision"
                            ? `/decision/${c.id}`
                            : c.type === "rule"
                            ? "/about#policies"
                            : "/evaluation"
                        }
                        className="inline-flex items-center gap-1 text-sm font-mono px-2 py-0.5 rounded-md bg-amber-400/10 text-amber-300 border border-amber-400/20 hover:bg-amber-400/20 transition"
                      >
                        {c.label}
                        <ExternalLink className="w-2.5 h-2.5" />
                      </Link>
                    ))}
                  </div>
                )}

                {/* Structured Scenario Preview */}
                {m.scenario_preview && (
                  <div className="mt-4 p-4 rounded-xl bg-navy-950/90 border border-amber-500/30 flex flex-col gap-3">
                    <div className="flex items-center gap-2 text-amber-400 font-bold text-sm uppercase tracking-wide">
                      <Zap className="w-4 h-4" />
                      {m.scenario_preview.title}
                    </div>
                    <div className="space-y-1.5 text-sm text-slate-300">
                      {m.scenario_preview.events.map((e, eIdx) => (
                        <div
                          key={eIdx}
                          className="flex items-center justify-between p-2 rounded bg-white/5 border border-white/5"
                        >
                          <span className="font-mono text-amber-300 uppercase">
                            {e.type}
                          </span>
                          <span className="text-slate-400">
                            {e.station_name || `${e.multiplier} (${e.temp_rise})`}
                          </span>
                        </div>
                      ))}
                    </div>
                    <p className="text-sm text-slate-400 italic">
                      {m.scenario_preview.projected_impact}
                    </p>
                    <div className="flex items-center justify-end pt-1">
                      {injectedScenarios[m.scenario_preview.title] ? (
                        <div className="flex items-center gap-1.5 text-sm font-semibold text-emerald-400 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                          <CheckCircle2 className="w-4 h-4" />
                          Scenario Injected into Twin
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() =>
                            handleConfirmScenario(m.scenario_preview!.title)
                          }
                          className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-navy-950 font-bold text-sm shadow-md transition"
                        >
                          Confirm & Inject Scenario
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Collapsible Tools Used Trace */}
                {m.tools_used && m.tools_used.length > 0 && (
                  <div className="mt-2 pt-2 text-sm">
                    <button
                      type="button"
                      onClick={() => toggleTools(idx)}
                      className="flex items-center gap-1 text-sm font-mono text-slate-400 hover:text-slate-300"
                    >
                      {expandedTools[idx] ? (
                        <ChevronDown className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5" />
                      )}
                      <span>Tools used ({m.tools_used.length})</span>
                    </button>
                    {expandedTools[idx] && (
                      <div className="mt-1.5 p-2 rounded bg-black/30 font-mono text-xs text-emerald-400 space-y-1">
                        {m.tools_used.map((tool, tIdx) => (
                          <div key={tIdx} className="truncate">
                            &gt; {tool}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-white/10 bg-navy-900/60">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend(inputVal);
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder="Ask why a plan was vetoed, or inspect metrics..."
              className="flex-1 px-4 py-2.5 rounded-full bg-white/5 border border-white/15 focus:border-amber-400/60 focus:outline-none text-base text-white placeholder:text-slate-400"
            />
            <button
              type="submit"
              disabled={!inputVal.trim()}
              aria-label="Send message to copilot"
              className="w-10 h-10 rounded-full bg-amber-500 disabled:opacity-40 hover:bg-amber-400 text-navy-950 flex items-center justify-center transition shadow-md"
            >
              <Send className="w-4 h-4 ml-0.5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
