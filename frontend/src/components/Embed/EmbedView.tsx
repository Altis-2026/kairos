import { useEffect, useMemo, useState } from "react";
import { Loader2, ExternalLink } from "lucide-react";
import Globe from "../Globe";
import { runAnalyze } from "../../api/analyze";
import { applyResultToGlobe } from "../../lib/applyResult";
import { parseEmbedHash } from "../../lib/embed";
import type { AnalysisResult } from "../../types/analysis";

export default function EmbedView() {
  const ref = useMemo(() => parseEmbedHash(), []);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const home = `${location.origin}${location.pathname}`;

  useEffect(() => {
    if (!ref) {
      setError("This embed link is missing or malformed.");
      return;
    }
    let cancelled = false;
    runAnalyze(ref)
      .then((r) => {
        if (cancelled) return;
        setResult(r);
        applyResultToGlobe(r);
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Could not load this analysis.")
      );
    return () => {
      cancelled = true;
    };
  }, [ref]);

  return (
    <div className="relative h-full w-full bg-bg overflow-hidden">
      <Globe />

      <div className="absolute left-3 top-3 z-30 rounded-xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel px-3.5 py-2.5 max-w-[70%]">
        {error ? (
          <p className="text-[11px] text-amber leading-snug">{error}</p>
        ) : !result ? (
          <div className="flex items-center gap-2 text-xs text-dim">
            <Loader2 size={13} className="animate-spin" /> Loading analysis…
          </div>
        ) : (
          <>
            <div className="text-[11px] text-ink font-medium truncate">
              {result.display_name}
            </div>
            <div className="mt-0.5 font-display text-2xl text-teal leading-none">
              {result.headline_stat.value.toLocaleString()}
              <span className="ml-1 text-xs text-dim">
                {result.headline_stat.unit}
              </span>
            </div>
            <div className="mt-1 font-mono text-[9px] text-dim">
              Sentinel-1 · {result.data_date}
            </div>
          </>
        )}
      </div>

      <a
        href={home}
        target="_blank"
        rel="noreferrer"
        className="absolute right-3 bottom-3 z-30 flex items-center gap-1.5 rounded-lg bg-surface/90 backdrop-blur ring-1 ring-line px-2.5 py-1.5 text-[10px] text-dim hover:text-teal transition"
        title="Open in Kairos"
      >
        <span className="font-display text-teal">Kairos</span>
        <span className="text-dim/70">SAR</span>
        <ExternalLink size={10} />
      </a>
    </div>
  );
}
