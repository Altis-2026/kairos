import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, X } from "lucide-react";
import { STEP_ORDER, useSidebarStore } from "../../stores/sidebarStore";
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
  const { open, step, closeSidebar, goToStep } = useSidebarStore();
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
          className="absolute z-40 max-sm:inset-x-3 max-sm:top-16 max-sm:bottom-20 sm:left-5 sm:top-20 sm:bottom-24 sm:w-[360px] flex flex-col rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel"
        >
          <div className="p-4 pb-3 space-y-3 border-b border-line">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] tracking-[0.22em] text-dim">
                NEW ANALYSIS
              </span>
              <button
                onClick={closeSidebar}
                className="text-dim hover:text-ink transition-colors"
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
