/** Step 6 — the result: headline, confidence, exports, next actions. */
import { useState } from "react";
import { Check, Copy, Download, GitCompareArrows, RotateCcw } from "lucide-react";
import { useSidebarStore } from "../../../stores/sidebarStore";

export default function ShowResult() {
  const { result, reset, compareNewDates, selectedTask } = useSidebarStore();
  const [copied, setCopied] = useState(false);

  if (!result) {
    return (
      <p className="text-xs text-dim">
        No result to show — run an analysis first.
      </p>
    );
  }

  const vesselPoints = result.stats?.vessel_points as
    | GeoJSON.FeatureCollection
    | undefined;

  function downloadGeoJSON() {
    if (!vesselPoints) return;
    const blob = new Blob([JSON.stringify(vesselPoints, null, 2)], {
      type: "application/geo+json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kairos-${result!.analysis_type}-${result!.data_date}.geojson`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function copyShareLink() {
    const params = new URLSearchParams({
      task: result!.analysis_type,
      bbox: result!.bbox.join(","),
      start: result!.start_date,
      end: result!.end_date,
    });
    navigator.clipboard
      .writeText(`${location.origin}${location.pathname}#${params.toString()}`)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-4">
        <div className="font-mono text-[10px] tracking-[0.18em] text-dim uppercase">
          {result.headline_stat.label}
        </div>
        <div className="mt-1 font-display text-4xl text-teal">
          {result.headline_stat.value.toLocaleString()}
          <span className="ml-1.5 text-lg text-dim">
            {result.headline_stat.unit}
          </span>
        </div>
        <div className="mt-2 font-mono text-[10px] text-dim">
          Sentinel-1 · {result.data_date} · confidence{" "}
          {Math.round(result.confidence * 100)}%
        </div>
      </div>

      {result.headline_stat.value === 0 && (
        <p className="text-[11px] text-dim leading-relaxed">
          No change detected in this window. That can be the real answer — or
          try different dates or a larger area.
        </p>
      )}

      <div className="space-y-2">
        <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
          Export
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={downloadGeoJSON}
            disabled={!vesselPoints}
            title={
              vesselPoints
                ? "Download detections as GeoJSON"
                : "GeoJSON export is available for point results (e.g. ships)"
            }
            className="h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition-colors disabled:opacity-40"
          >
            <Download size={13} /> GeoJSON
          </button>
          <button
            disabled
            title="GeoTIFF export ships in Phase 2"
            className="h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim opacity-40"
          >
            <Download size={13} /> GeoTIFF
          </button>
        </div>
        <button
          onClick={copyShareLink}
          className="w-full h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition-colors"
        >
          {copied ? <Check size={13} className="text-teal" /> : <Copy size={13} />}
          {copied ? "Link copied" : "Copy share link"}
        </button>
      </div>

      <div className="space-y-2">
        <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
          Next
        </h3>
        <button
          onClick={compareNewDates}
          className="w-full h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition-colors"
        >
          <GitCompareArrows size={13} /> Compare different dates ·{" "}
          {selectedTask?.display_name}
        </button>
        <button
          onClick={reset}
          className="w-full h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition-colors"
        >
          <RotateCcw size={13} /> New analysis
        </button>
      </div>
    </div>
  );
}
