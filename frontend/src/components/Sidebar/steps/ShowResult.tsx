import { useState } from "react";
import {
  Check,
  Code2,
  Copy,
  Download,
  FileText,
  GitCompareArrows,
  Loader2,
  RotateCcw,
} from "lucide-react";
import { useSidebarStore } from "../../../stores/sidebarStore";
import {
  downloadGeoTIFF,
  downloadReport,
  type ExportSource,
} from "../../../lib/exporters";
import { buildShareUrl } from "../../../lib/share";
import { buildEmbedSnippet } from "../../../lib/embed";
import ResultInsight from "../../Insight/ResultInsight";

export default function ShowResult() {
  const { result, reset, compareNewDates, selectedTask } = useSidebarStore();
  const [copied, setCopied] = useState(false);
  const [embedCopied, setEmbedCopied] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [exportErr, setExportErr] = useState<string | null>(null);

  if (!result) {
    return (
      <p className="text-xs text-dim">
        No result to show. Run an analysis first.
      </p>
    );
  }

  const vesselPoints = result.stats?.vessel_points as
    | GeoJSON.FeatureCollection
    | undefined;

  const exportSrc: ExportSource = {
    analysis_type: result.analysis_type,
    display_name: result.display_name,
    bbox: result.bbox,
    start_date: result.start_date,
    end_date: result.end_date,
    data_date: result.data_date,
    confidence: result.confidence,
    headline_label: result.headline_stat.label,
    headline_value: result.headline_stat.value,
    headline_unit: result.headline_stat.unit,
    stats: result.stats,
  };

  async function runExport(key: string, fn: () => Promise<void>) {
    setBusy(key);
    setExportErr(null);
    try {
      await fn();
    } catch (e) {
      setExportErr(e instanceof Error ? e.message : "Export failed.");
    } finally {
      setBusy(null);
    }
  }

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
    navigator.clipboard
      .writeText(
        buildShareUrl({
          analysis_type: result!.analysis_type,
          bbox: result!.bbox,
          start_date: result!.start_date,
          end_date: result!.end_date,
        })
      )
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
  }

  function copyEmbedCode() {
    navigator.clipboard
      .writeText(
        buildEmbedSnippet({
          analysis_type: result!.analysis_type,
          bbox: result!.bbox,
          start_date: result!.start_date,
          end_date: result!.end_date,
        })
      )
      .then(() => {
        setEmbedCopied(true);
        setTimeout(() => setEmbedCopied(false), 2000);
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
          No change detected in this window. That can be the real answer, or
          try different dates or a larger area.
        </p>
      )}

      <ResultInsight
        input={{
          analysis_type: result.analysis_type,
          display_name: result.display_name,
          bbox: result.bbox,
          start_date: result.start_date,
          end_date: result.end_date,
          data_date: result.data_date,
          confidence: result.confidence,
          headline_label: result.headline_stat.label,
          headline_value: result.headline_stat.value,
          headline_unit: result.headline_stat.unit,
          stats: result.stats,
        }}
      />

      <div className="space-y-2">
        <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
          Export
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => runExport("geotiff", () => downloadGeoTIFF(exportSrc))}
            disabled={busy === "geotiff"}
            title="Download the result raster as a GeoTIFF"
            className="h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition-colors disabled:opacity-50"
          >
            {busy === "geotiff" ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Download size={13} />
            )}
            GeoTIFF
          </button>
          <button
            onClick={() => runExport("report", () => downloadReport(exportSrc))}
            disabled={busy === "report"}
            title="Download a methodology report (markdown)"
            className="h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition-colors disabled:opacity-50"
          >
            {busy === "report" ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <FileText size={13} />
            )}
            Report
          </button>
        </div>
        {vesselPoints && (
          <button
            onClick={downloadGeoJSON}
            title="Download detections as GeoJSON"
            className="w-full h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition-colors"
          >
            <Download size={13} /> GeoJSON (points)
          </button>
        )}
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={copyShareLink}
            className="h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition-colors"
          >
            {copied ? <Check size={13} className="text-teal" /> : <Copy size={13} />}
            {copied ? "Copied" : "Share link"}
          </button>
          <button
            onClick={copyEmbedCode}
            title="Copy an <iframe> snippet to embed this live result"
            className="h-9 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition-colors"
          >
            {embedCopied ? (
              <Check size={13} className="text-teal" />
            ) : (
              <Code2 size={13} />
            )}
            {embedCopied ? "Copied" : "Embed code"}
          </button>
        </div>
        {exportErr && (
          <p className="text-[10px] text-amber leading-snug">{exportErr}</p>
        )}
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
