import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowUpRight,
  Image as ImageIcon,
  Loader2,
  Radar,
  Sparkles,
  X,
} from "lucide-react";
import { useMapStore } from "../../stores/mapStore";
import { runAnalyze } from "../../api/analyze";
import { fetchOptical } from "../../api/research";
import { fetchInterpretation } from "../../api/interpret";
import { applyResultToGlobe } from "../../lib/applyResult";
import { buildShareUrl } from "../../lib/share";
import {
  eventBbox,
  eventWindow,
  planForEvent,
} from "../../lib/watchAnalysis";
import type { AnalysisResult, EventMarker } from "../../types/analysis";

const OPTICAL_ID = "watch-optical";

export default function WatchEventDetail({
  event,
  onClose,
}: {
  event: EventMarker;
  onClose: () => void;
}) {
  const plan = planForEvent(event);
  const bbox = eventBbox(event);
  const dates = eventWindow(event);

  const [busy, setBusy] = useState<null | "analyze" | "optical" | "explain">(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);

  useEffect(() => {
    setBusy(null);
    setError(null);
    setResult(null);
    setExplanation(null);
    useMapStore.getState().removeLayer(OPTICAL_ID);
  }, [event.id]);

  async function analyze() {
    setBusy("analyze");
    setError(null);
    try {
      const res = await runAnalyze({
        analysis_type: plan.analysisType,
        bbox,
        start_date: dates.start_date,
        end_date: dates.end_date,
      });
      setResult(res);
      applyResultToGlobe(res);

      setBusy("explain");
      try {
        const ix = await fetchInterpretation({
          analysis_type: res.analysis_type,
          display_name: res.display_name,
          bbox: res.bbox,
          start_date: res.start_date,
          end_date: res.end_date,
          data_date: res.data_date,
          confidence: res.confidence,
          headline_label: res.headline_stat.label,
          headline_value: res.headline_stat.value,
          headline_unit: res.headline_stat.unit,
          stats: res.stats,
        });
        if (ix.available && ix.text) setExplanation(ix.text);
      } catch {

      }
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "No Sentinel-1 data for this footprint yet. Try the full workspace."
      );
    } finally {
      setBusy(null);
    }
  }

  async function optical() {
    setBusy("optical");
    setError(null);
    try {
      const data = await fetchOptical({
        bbox,
        start_date: dates.start_date,
        end_date: dates.end_date,
      });
      const map = useMapStore.getState();
      map.addRasterLayer({
        id: OPTICAL_ID,
        name: data.label,
        tileUrl: data.tile_url,
        opacity: 1,
        visible: true,
        color: data.color,
      });
      map.requestFlyTo([event.lon, event.lat], 8);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No clear optical scene here.");
    } finally {
      setBusy(null);
    }
  }

  function openWorkspace() {
    const url = buildShareUrl({
      analysis_type: plan.analysisType,
      bbox,
      start_date: dates.start_date,
      end_date: dates.end_date,
    });
    window.location.href = url;
  }

  const blocks = (explanation ?? "")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  return (
    <motion.aside
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 24 }}
      className="absolute right-5 bottom-5 z-40 w-80 max-h-[70vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-3"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 font-mono text-[9px] tracking-[0.18em] text-amber uppercase">
            <span
              className="h-2 w-2 rounded-full"
              style={{ background: event.color }}
            />
            {event.category}
            {event.date && ` · ${event.date}`}
          </div>
          <h2 className="font-display text-base text-ink leading-tight mt-1">
            {event.title}
          </h2>
        </div>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      <p className="text-[11px] text-teal/90 leading-snug rounded-xl bg-bg/60 ring-1 ring-line px-3 py-2">
        {plan.pitch}
      </p>

      {result && (
        <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-3">
          <div className="font-mono text-[9px] tracking-[0.15em] text-dim uppercase">
            {result.headline_stat.label}
          </div>
          <div className="mt-0.5 font-display text-2xl text-teal leading-none">
            {result.headline_stat.value.toLocaleString()}
            <span className="ml-1 text-xs text-dim">
              {result.headline_stat.unit}
            </span>
          </div>
          <div className="mt-1 font-mono text-[9px] text-dim">
            {result.display_name} · {result.data_date} ·{" "}
            {Math.round(result.confidence * 100)}% confidence
          </div>
        </div>
      )}

      {(busy === "explain" || blocks.length > 0) && (
        <div className="rounded-xl bg-bg/60 ring-1 ring-line p-3 space-y-1.5">
          {busy === "explain" ? (
            <div className="flex items-center gap-2 text-[11px] text-dim">
              <Loader2 size={12} className="animate-spin" /> Reading the result…
            </div>
          ) : (
            blocks.map((b, i) =>
              b.startsWith("###") ? (
                <div
                  key={i}
                  className="font-mono text-[9px] tracking-[0.15em] text-teal uppercase pt-1"
                >
                  {b.replace(/^#+\s*/, "")}
                </div>
              ) : (
                <p key={i} className="text-[11px] text-dim leading-relaxed">
                  {b.replace(/\*\*/g, "").replace(/_/g, "")}
                </p>
              )
            )
          )}
        </div>
      )}

      {error && (
        <p className="text-[10px] text-amber leading-snug px-1">{error}</p>
      )}

      <div className="space-y-2">
        <button
          onClick={analyze}
          disabled={busy === "analyze" || busy === "explain"}
          className="w-full h-10 rounded-xl bg-amber text-bg font-medium text-sm flex items-center justify-center gap-2 hover:brightness-110 transition disabled:opacity-60"
        >
          {busy === "analyze" ? (
            <Loader2 size={15} className="animate-spin" />
          ) : (
            <Radar size={15} />
          )}
          {result ? "Re-run analysis" : "Analyze with Kairos"}
        </button>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={optical}
            disabled={busy === "optical"}
            className="h-9 rounded-xl text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition disabled:opacity-50"
          >
            {busy === "optical" ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <ImageIcon size={12} />
            )}
            Optical
          </button>
          <button
            onClick={openWorkspace}
            className="h-9 rounded-xl text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition"
          >
            <ArrowUpRight size={12} />
            Workspace
          </button>
        </div>
      </div>

      <div className="flex items-center gap-1.5 pt-0.5 text-[9px] text-dim font-mono">
        <Sparkles size={10} className="text-teal" />
        Live analysis on free ESA Sentinel-1 radar
      </div>
    </motion.aside>
  );
}
