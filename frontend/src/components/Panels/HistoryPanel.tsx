import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Clock, Loader2, RotateCcw, Share2, Trash2, X, Check } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { useCasesStore } from "../../stores/casesStore";
import { casesAvailable, deleteCase, loadCases } from "../../lib/cases";
import { buildShareUrl } from "../../lib/share";
import { runAnalyze } from "../../api/analyze";
import { applyResultToGlobe } from "../../lib/applyResult";
import type { SavedCase } from "../../stores/casesStore";

export default function HistoryPanel({ onClose }: { onClose: () => void }) {
  const user = useAuthStore((s) => s.user);
  const { cases, loading, error } = useCasesStore();
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    if (user) loadCases();
  }, [user]);

  async function restore(c: SavedCase) {
    setRestoringId(c.id);
    try {
      const result = await runAnalyze({
        analysis_type: c.analysisType,
        bbox: c.bbox,
        start_date: c.startDate,
        end_date: c.endDate,
      });
      applyResultToGlobe(result);
      onClose();
    } catch {

    } finally {
      setRestoringId(null);
    }
  }

  function share(c: SavedCase) {
    const url = buildShareUrl({
      analysis_type: c.analysisType,
      bbox: c.bbox,
      start_date: c.startDate,
      end_date: c.endDate,
    });
    navigator.clipboard.writeText(url).then(() => {
      setCopiedId(c.id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  }

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[58dvh] sm:right-20 sm:top-1/2 sm:-translate-y-1/2 sm:w-80 sm:max-h-[82vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-dim">
          <Clock size={12} /> MY ANALYSES
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      {!casesAvailable() ? (
        <p className="text-xs text-dim leading-relaxed">
          Saved analyses need Firebase configured. Add the{" "}
          <span className="font-mono text-teal">VITE_FIREBASE_*</span> values to
          enable history.
        </p>
      ) : !user ? (
        <p className="text-xs text-dim leading-relaxed">
          Sign in to automatically save every analysis you run and pick up where
          you left off.
        </p>
      ) : loading ? (
        <div className="flex items-center gap-2 text-xs text-dim">
          <Loader2 size={14} className="animate-spin" /> Loading saved analyses…
        </div>
      ) : error ? (
        <p className="text-[11px] text-amber leading-relaxed">{error}</p>
      ) : cases.length === 0 ? (
        <p className="text-xs text-dim leading-relaxed">
          No saved analyses yet. Run one and it'll appear here automatically.
        </p>
      ) : (
        <ul className="space-y-2 max-h-[26rem] overflow-y-auto">
          {cases.map((c) => (
            <li
              key={c.id}
              className="rounded-xl bg-bg/70 ring-1 ring-line p-3 space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-xs text-ink truncate">{c.displayName}</div>
                  <div className="font-mono text-[10px] text-dim mt-0.5">
                    {c.headlineValue.toLocaleString()} {c.headlineUnit} ·{" "}
                    {c.dataDate}
                  </div>
                </div>
                <span className="font-mono text-[9px] text-dim/70 shrink-0">
                  {new Date(c.createdAt).toLocaleDateString()}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => restore(c)}
                  disabled={restoringId === c.id}
                  className="flex-1 h-8 rounded-lg text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-teal hover:ring-teal/40 transition disabled:opacity-50"
                  title="Re-run this analysis"
                >
                  {restoringId === c.id ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <RotateCcw size={12} />
                  )}
                  Restore
                </button>
                <button
                  onClick={() => share(c)}
                  className="h-8 w-8 grid place-items-center rounded-lg ring-1 ring-line text-dim hover:text-ink transition"
                  title="Copy shareable link"
                >
                  {copiedId === c.id ? (
                    <Check size={12} className="text-teal" />
                  ) : (
                    <Share2 size={12} />
                  )}
                </button>
                <button
                  onClick={() => deleteCase(c.id)}
                  className="h-8 w-8 grid place-items-center rounded-lg ring-1 ring-line text-dim hover:text-ink transition"
                  title="Delete"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </motion.aside>
  );
}
