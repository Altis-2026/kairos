import { useState } from "react";
import { motion } from "framer-motion";
import { Bot, Check, Loader2, Sparkles, X } from "lucide-react";
import { useMapStore } from "../../stores/mapStore";
import {
  missionReport,
  planMission,
  type MissionOutcome,
  type MissionStep,
} from "../../api/agent";
import { runAnalyze } from "../../api/analyze";
import { applyResultToGlobe } from "../../lib/applyResult";

type StepState = "pending" | "running" | "ok" | "no_data" | "failed";

interface TrackedStep {
  step: MissionStep;
  state: StepState;
  detail?: string;
}

const EXAMPLES = [
  "Find the newest deforestation across the Amazon this month",
  "Compare flood risk in Houston and New Orleans right now",
  "Check every kind of stress on California's Central Valley farmland",
];

export default function AgentPanel({ onClose }: { onClose: () => void }) {
  const [goal, setGoal] = useState("");
  const [phase, setPhase] = useState<"idle" | "planning" | "running" | "done">("idle");
  const [planSummary, setPlanSummary] = useState<string | null>(null);
  const [steps, setSteps] = useState<TrackedStep[]>([]);
  const [report, setReport] = useState<string | null>(null);
  const [clarification, setClarification] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(missionGoal: string) {
    const trimmed = missionGoal.trim();
    if (!trimmed || phase === "planning" || phase === "running") return;
    setPhase("planning");
    setError(null);
    setClarification(null);
    setReport(null);
    setSteps([]);
    setPlanSummary(null);

    let plan;
    try {
      const viewport = useMapStore.getState().viewportBbox ?? undefined;
      plan = await planMission(trimmed, viewport);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Mission planning failed.");
      setPhase("idle");
      return;
    }

    if (!plan.understood || !plan.steps?.length) {
      setClarification(
        plan.clarification ?? "I could not turn that into a plan. Try being more specific."
      );
      setPhase("idle");
      return;
    }

    setPlanSummary(plan.plan_summary);
    const tracked: TrackedStep[] = plan.steps.map((step) => ({ step, state: "pending" }));
    setSteps(tracked);
    setPhase("running");

    const outcomes: MissionOutcome[] = [];
    for (let i = 0; i < tracked.length; i++) {
      setSteps((prev) =>
        prev.map((t, idx) => (idx === i ? { ...t, state: "running" } : t))
      );
      const step = tracked[i].step;
      try {
        const result = await runAnalyze({
          analysis_type: step.analysis_type,
          bbox: step.bbox,
          start_date: step.start_date,
          end_date: step.end_date,
        });
        applyResultToGlobe(result);
        outcomes.push({
          analysis_type: step.analysis_type,
          display_name: result.display_name,
          location_name: step.location_name,
          status: "ok",
          headline_label: result.headline_stat.label,
          headline_value: result.headline_stat.value,
          headline_unit: result.headline_stat.unit,
          data_date: result.data_date,
        });
        setSteps((prev) =>
          prev.map((t, idx) =>
            idx === i
              ? {
                  ...t,
                  state: "ok",
                  detail: `${result.headline_stat.label}: ${result.headline_stat.value} ${result.headline_stat.unit}`,
                }
              : t
          )
        );
      } catch (e) {
        const msg = e instanceof Error ? e.message : "failed";
        const noData = /no .*data|not available/i.test(msg);
        outcomes.push({
          analysis_type: step.analysis_type,
          location_name: step.location_name,
          status: noData ? "no_data" : "failed",
          detail: msg,
        });
        setSteps((prev) =>
          prev.map((t, idx) =>
            idx === i
              ? { ...t, state: noData ? "no_data" : "failed", detail: noData ? "No radar data in the window" : msg }
              : t
          )
        );
      }
    }

    try {
      const res = await missionReport({
        goal: trimmed,
        plan_summary: plan.plan_summary,
        outcomes,
      });
      setReport(res.report);
    } catch {
      const ok = outcomes.filter((o) => o.status === "ok").length;
      setReport(`Mission finished. ${ok} of ${outcomes.length} analyses completed and are on the globe.`);
    }
    setPhase("done");
  }

  function reset() {
    setPhase("idle");
    setSteps([]);
    setReport(null);
    setPlanSummary(null);
    setClarification(null);
    setError(null);
  }

  const busy = phase === "planning" || phase === "running";

  const dot = (state: StepState) => {
    if (state === "running") return <Loader2 size={13} className="animate-spin text-amber" />;
    if (state === "ok") return <Check size={13} className="text-teal" />;
    if (state === "no_data") return <span className="text-dim text-[10px] font-mono">--</span>;
    if (state === "failed") return <X size={13} className="text-amber" />;
    return <span className="h-2 w-2 rounded-full bg-line inline-block" />;
  };

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[62dvh] sm:right-20 sm:top-1/2 sm:-translate-y-1/2 sm:w-[22rem] sm:max-h-[84vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-dim">
          <Bot size={13} className="text-amber" /> AGENT MODE
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      <p className="text-xs text-dim leading-relaxed">
        Give one goal instead of one question. Kairos plans a set of radar
        analyses, runs each one, and writes back what it found across all of them.
      </p>

      <div className="space-y-2">
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g. find the newest deforestation across the Amazon this month"
          rows={2}
          disabled={busy}
          aria-label="Mission goal"
          className="w-full rounded-xl bg-bg/70 ring-1 ring-line px-3 py-2.5 text-xs text-ink placeholder-dim outline-none focus:ring-amber/60 resize-none disabled:opacity-60"
        />
        <button
          onClick={() => run(goal)}
          disabled={busy || !goal.trim()}
          className="w-full h-10 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition disabled:opacity-40 flex items-center justify-center gap-2"
        >
          {phase === "planning" ? (
            <>
              <Loader2 size={14} className="animate-spin" /> Planning the mission…
            </>
          ) : phase === "running" ? (
            <>
              <Loader2 size={14} className="animate-spin" /> Running…
            </>
          ) : (
            <>
              <Sparkles size={14} /> Launch mission
            </>
          )}
        </button>
      </div>

      {phase === "idle" && !clarification && (
        <div className="space-y-1.5">
          <span className="font-mono text-[10px] tracking-[0.2em] text-dim">TRY</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => {
                setGoal(ex);
                run(ex);
              }}
              className="w-full text-left rounded-xl bg-bg/70 ring-1 ring-line px-3 py-2 text-[11px] text-dim hover:text-ink hover:ring-teal/40 transition"
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      {clarification && (
        <div className="rounded-xl bg-bg/70 ring-1 ring-amber/40 p-3 text-[11px] text-ink leading-relaxed">
          {clarification}
        </div>
      )}

      {planSummary && (
        <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-3">
          <div className="font-mono text-[9px] tracking-[0.2em] text-dim mb-1">PLAN</div>
          <p className="text-[11px] text-ink leading-relaxed">{planSummary}</p>
        </div>
      )}

      {steps.length > 0 && (
        <ol className="space-y-1.5">
          {steps.map((t, i) => (
            <li
              key={i}
              className="flex items-start gap-2.5 rounded-xl bg-bg/70 ring-1 ring-line p-2.5"
            >
              <span className="mt-0.5 w-4 grid place-items-center shrink-0">
                {dot(t.state)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[11px] text-ink">
                  {t.step.analysis_type.replace(/_/g, " ")} ·{" "}
                  {t.step.location_name ?? "target area"}
                </span>
                {t.step.purpose && (
                  <span className="block text-[10px] text-dim leading-tight">
                    {t.step.purpose}
                  </span>
                )}
                {t.detail && (
                  <span className="block text-[10px] text-teal leading-tight mt-0.5">
                    {t.detail}
                  </span>
                )}
              </span>
            </li>
          ))}
        </ol>
      )}

      {report && (
        <div className="rounded-xl bg-raised ring-1 ring-teal/40 p-3 space-y-2">
          <div className="font-mono text-[9px] tracking-[0.2em] text-teal">
            MISSION REPORT
          </div>
          <p className="text-xs text-ink leading-relaxed">{report}</p>
          <button
            onClick={reset}
            className="text-[11px] text-dim hover:text-ink underline underline-offset-2"
          >
            New mission
          </button>
        </div>
      )}

      {error && <p className="text-[11px] text-amber leading-snug">{error}</p>}
    </motion.aside>
  );
}
