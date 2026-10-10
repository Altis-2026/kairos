import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, X } from "lucide-react";
import { STEP_ORDER, useSidebarStore } from "../../stores/sidebarStore";
import { useMapStore } from "../../stores/mapStore";
import { panelShellFlex } from "../../lib/responsive";
import StepIndicator from "./StepIndicator";
import SelectTask from "./steps/SelectTask";
import DefineAOI from "./steps/DefineAOI";
import Configure from "./steps/Configure";
import PreviewScenes from "./steps/PreviewScenes";
import RunAnalysis from "./steps/RunAnalysis";
import ShowResult from "./steps/ShowResult";

const TITLES: Record<string, string> = {
  SELECT_TASK: "What do you want to find?",
  DEFINE_AOI: "Where should it look?",
  CONFIGURE: "When, and against what baseline?",
  PREVIEW_SCENES: "Data availability",
  RUNNING: "Running analysis",
  RESULT: "Result",
};

export default function Sidebar() {
  const open = useSidebarStore((s) => s.open);
  const step = useSidebarStore((s) => s.step);
  const closeSidebar = useSidebarStore((s) => s.closeSidebar);
  const goToStep = useSidebarStore((s) => s.goToStep);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !useMapStore.getState().drawMode) closeSidebar();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, closeSidebar]);
  const stepIdx = STEP_ORDER.indexOf(step);
  const canGoBack = stepIdx > 0 && step !== "RUNNING";

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          initial={{ x: -420, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -420, opacity: 0 }}
          transition={{ type: "spring", stiffness: 320, damping: 32 }}
          className={panelShellFlex("lg:left-5 lg:right-auto lg:top-20 lg:bottom-24 lg:w-[360px]")}
        >
          <div className="p-4 pb-3 space-y-3 border-b border-line">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] tracking-[0.22em] text-dim">NEW ANALYSIS</span>
              <button
                onClick={closeSidebar}
                className="text-dim hover:text-ink transition-colors"
                aria-label="Close"
                title="Close"
              >
                <X size={15} />
              </button>
            </div>
            <StepIndicator />
            <div className="flex items-center gap-2">
              {canGoBack && (
                <button
                  onClick={() => goToStep(STEP_ORDER[stepIdx - 1])}
                  className="text-dim hover:text-ink transition-colors"
                  aria-label="Back"
                  title="Back"
                >
                  <ArrowLeft size={15} />
                </button>
              )}
              <h2 className="font-display text-base text-ink">{TITLES[step]}</h2>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {step === "SELECT_TASK" && <SelectTask />}
            {step === "DEFINE_AOI" && <DefineAOI />}
            {step === "CONFIGURE" && <Configure />}
            {step === "PREVIEW_SCENES" && <PreviewScenes />}
            {step === "RUNNING" && <RunAnalysis />}
            {step === "RESULT" && <ShowResult />}
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
