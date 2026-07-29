import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { apiConfigProblem } from "../api/client";

export default function SetupNotice() {
  const [dismissed, setDismissed] = useState(false);
  const problem = apiConfigProblem();

  if (!problem || dismissed) return null;

  return (
    <div className="absolute top-16 inset-x-3 sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2 sm:max-w-lg z-50 rounded-xl bg-surface ring-1 ring-amber/60 shadow-panel p-3 flex items-start gap-2.5">
      <AlertTriangle size={15} className="text-amber shrink-0 mt-0.5" />
      <div className="min-w-0 flex-1">
        <div className="font-mono text-[10px] tracking-[0.18em] text-amber uppercase">
          Setup needed
        </div>
        <p className="mt-1 text-[11px] text-dim leading-relaxed">{problem}</p>
      </div>
      <button
        onClick={() => setDismissed(true)}
        title="Dismiss"
        className="text-dim hover:text-ink shrink-0"
      >
        <X size={14} />
      </button>
    </div>
  );
}
