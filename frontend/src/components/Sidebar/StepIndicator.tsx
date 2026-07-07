import { useSidebarStore, STEP_ORDER, type SidebarStep } from "../../stores/sidebarStore";

const LABELS: Record<SidebarStep, string> = {
  SELECT_TASK: "Task",
  DEFINE_AOI: "Area",
  CONFIGURE: "Configure",
  PREVIEW_SCENES: "Scenes",
  RUNNING: "Run",
  RESULT: "Result",
};

export default function StepIndicator() {
  const step = useSidebarStore((s) => s.step);
  const goToStep = useSidebarStore((s) => s.goToStep);
  const selectedTask = useSidebarStore((s) => s.selectedTask);
  const currentIdx = STEP_ORDER.indexOf(step);

  return (
    <ol className="flex items-center gap-1">
      {STEP_ORDER.map((s, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;

        const clickable = done && step !== "RUNNING" && (i > 0 ? !!selectedTask : true);
        return (
          <li key={s} className="flex items-center gap-1">
            <button
              disabled={!clickable}
              onClick={() => clickable && goToStep(s)}
              className={`h-6 px-2 rounded-md font-mono text-[9px] tracking-[0.12em] uppercase transition-colors ${
                active
                  ? "bg-raised text-teal ring-1 ring-teal/40"
                  : done
                  ? "text-ink hover:text-teal"
                  : "text-dim/60"
              } ${clickable ? "cursor-pointer" : "cursor-default"}`}
            >
              {LABELS[s]}
            </button>
            {i < STEP_ORDER.length - 1 && (
              <span className={`h-px w-2 ${done ? "bg-teal/50" : "bg-line"}`} />
            )}
          </li>
        );
      })}
    </ol>
  );
}
