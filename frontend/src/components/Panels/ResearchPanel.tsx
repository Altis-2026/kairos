import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Bell,
  Building2,
  Check,
  Code2,
  Download,
  FileText,
  GitCompareArrows,
  Image as ImageIcon,
  Loader2,
  Radar,
  Share2,
  Timer,
  Users,
  UsersRound,
  X,
} from "lucide-react";
import { useMapStore } from "../../stores/mapStore";
import { useAuthStore } from "../../stores/authStore";
import { createAlert, alertsAvailable } from "../../lib/alerts";
import {
  fetchBackscatter,
  fetchCompare,
  fetchOptical,
  fetchPopulationDensity,
  fetchTimeSeries,
  type AnalysisRef,
} from "../../api/research";
import { fetchImpact } from "../../api/impact";
import { buildEmbedSnippet } from "../../lib/embed";
import ResultInsight from "../Insight/ResultInsight";
import type { ImpactResponse } from "../../types/analysis";
import {
  downloadGeoTIFF,
  downloadReport,
  type ExportSource,
} from "../../lib/exporters";
import { buildShareUrl } from "../../lib/share";

const BACKSCATTER_ID = "research-backscatter";
const OPTICAL_ID = "research-optical";
const POPULATION_ID = "research-population";

export default function ResearchPanel({ onClose }: { onClose: () => void }) {
  const lastResult = useMapStore((s) => s.lastResult);
  const layers = useMapStore((s) => s.layers);
  const compare = useMapStore((s) => s.compare);
  const timeline = useMapStore((s) => s.timeline);

  const user = useAuthStore((s) => s.user);
  const [busy, setBusy] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [copied, setCopied] = useState(false);
  const [impact, setImpact] = useState<ImpactResponse | null>(null);
  const [watched, setWatched] = useState(false);
  const [embedCopied, setEmbedCopied] = useState(false);

  const ref: AnalysisRef | null = lastResult
    ? {
        analysis_type: lastResult.analysisType,
        bbox: lastResult.bbox,
        start_date: lastResult.startDate,
        end_date: lastResult.endDate,
      }
    : null;

  const exportSrc: ExportSource | null = lastResult
    ? {
        analysis_type: lastResult.analysisType,
        display_name: lastResult.displayName,
        bbox: lastResult.bbox,
        start_date: lastResult.startDate,
        end_date: lastResult.endDate,
        data_date: lastResult.dataDate,
        confidence: lastResult.confidence,
        headline_label: lastResult.headlineLabel,
        headline_value: lastResult.headlineValue,
        headline_unit: lastResult.headlineUnit,
        stats: lastResult.stats,
      }
    : null;

  function copyShare() {
    if (!ref) return;
    navigator.clipboard.writeText(buildShareUrl(ref)).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function copyEmbed() {
    if (!ref) return;
    navigator.clipboard.writeText(buildEmbedSnippet(ref)).then(() => {
      setEmbedCopied(true);
      setTimeout(() => setEmbedCopied(false), 2000);
    });
  }

  const backscatterOn = layers.some((l) => l.id === BACKSCATTER_ID);
  const opticalOn = layers.some((l) => l.id === OPTICAL_ID);
  const populationOn = layers.some((l) => l.id === POPULATION_ID);

  useEffect(() => {
    setImpact(null);
    setWatched(false);
  }, [lastResult]);

  async function watchArea() {
    if (!lastResult) return;
    await guard("watch", async () => {
      await createAlert(lastResult);
      setWatched(true);
    });
  }

  async function runImpact() {
    if (!ref) return;
    await guard("impact", async () => {
      const data = await fetchImpact(ref);
      setImpact(data);
    });
  }

  function setError(key: string, msg: string | null) {
    setErrors((e) => {
      const next = { ...e };
      if (msg) next[key] = msg;
      else delete next[key];
      return next;
    });
  }

  async function guard(key: string, fn: () => Promise<void>) {
    setBusy(key);
    setError(key, null);
    try {
      await fn();
    } catch (e) {
      setError(key, e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  }

  async function toggleBackscatter() {
    if (!ref) return;
    const map = useMapStore.getState();
    if (backscatterOn) {
      map.removeLayer(BACKSCATTER_ID);
      return;
    }
    await guard("backscatter", async () => {
      const data = await fetchBackscatter(ref);
      map.addRasterLayer({
        id: BACKSCATTER_ID,
        name: `${data.label} · ${data.data_date}`,
        tileUrl: data.tile_url,
        opacity: 0.9,
        visible: true,
        color: data.color,
      });
    });
  }

  async function toggleOptical() {
    if (!ref) return;
    const map = useMapStore.getState();
    if (opticalOn) {
      map.removeLayer(OPTICAL_ID);
      return;
    }
    await guard("optical", async () => {
      const data = await fetchOptical({
        bbox: ref.bbox,
        start_date: ref.start_date,
        end_date: ref.end_date,
      });
      const cloud =
        data.cloud_percent != null ? ` · ${data.cloud_percent}% cloud` : "";
      map.addRasterLayer({
        id: OPTICAL_ID,
        name: `${data.label}${cloud}`,
        tileUrl: data.tile_url,
        opacity: 1,
        visible: true,
        color: data.color,
      });
    });
  }

  async function togglePopulation() {
    if (!ref) return;
    const map = useMapStore.getState();
    if (populationOn) {
      map.removeLayer(POPULATION_ID);
      return;
    }
    await guard("population", async () => {
      const data = await fetchPopulationDensity({ bbox: ref.bbox });
      map.addRasterLayer({
        id: POPULATION_ID,
        name: data.label,
        tileUrl: data.tile_url,
        opacity: 0.75,
        visible: true,
        color: data.color,
      });
    });
  }

  async function toggleCompare() {
    if (!ref) return;
    const map = useMapStore.getState();
    if (compare) {
      map.clearGroup("compare");
      map.setCompare(null);
      return;
    }
    await guard("compare", async () => {
      const data = await fetchCompare(ref);
      const beforeId = "research-compare-before";
      const afterId = "research-compare-after";
      map.addRasterLayer({
        id: beforeId,
        name: data.before.label,
        tileUrl: data.before.tile_url,
        opacity: 1,
        visible: true,
        color: "#9CA3AF",
        group: "compare",
      });
      map.addRasterLayer({
        id: afterId,
        name: data.after.label,
        tileUrl: data.after.tile_url,
        opacity: 0.5,
        visible: true,
        color: "#9CA3AF",
        group: "compare",
      });
      map.setCompare({
        beforeLayerId: beforeId,
        afterLayerId: afterId,
        beforeLabel: data.before.label,
        afterLabel: data.after.label,
      });
    });
  }

  async function toggleTimeline() {
    if (!ref) return;
    const map = useMapStore.getState();
    if (timeline) {
      map.clearGroup("timeline");
      map.setTimeline(null);
      return;
    }
    await guard("timeline", async () => {
      const data = await fetchTimeSeries({
        analysis_type: ref.analysis_type,
        bbox: ref.bbox,
        end_date: ref.end_date,
      });
      const lastIdx = data.frames.length - 1;
      const frames = data.frames.map((f, i) => {
        const layerId = `research-ts-${i}`;
        map.addRasterLayer({
          id: layerId,
          name: `${f.date}`,
          tileUrl: f.tile_url,
          opacity: 0.9,
          visible: i === lastIdx,
          color: "#00BFA8",
          group: "timeline",
        });
        return { layerId, date: f.date, value: f.value };
      });
      map.setTimeline({ frames, unit: data.unit, metric: data.metric });
      map.setTimelineIndex(lastIdx);
    });
  }

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[58dvh] sm:right-20 sm:top-1/2 sm:-translate-y-1/2 sm:w-80 sm:max-h-[82vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
          RESEARCH TOOLS
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      {!lastResult ? (
        <p className="text-xs text-dim leading-relaxed">
          Run an analysis first, from the sidebar, the chat, or the ⚡ quick-pin.
          These tools build on the most recent result.
        </p>
      ) : (
        <>
          <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3">
            <div className="text-xs text-ink truncate">
              {lastResult.displayName}
            </div>
            <div className="mt-0.5 font-mono text-[10px] text-dim">
              {lastResult.dataDate} · {lastResult.startDate} → {lastResult.endDate}
            </div>
          </div>

          <ResultInsight
            input={{
              analysis_type: lastResult.analysisType,
              display_name: lastResult.displayName,
              bbox: lastResult.bbox,
              start_date: lastResult.startDate,
              end_date: lastResult.endDate,
              data_date: lastResult.dataDate,
              confidence: lastResult.confidence,
              headline_label: lastResult.headlineLabel,
              headline_value: lastResult.headlineValue,
              headline_unit: lastResult.headlineUnit,
              stats: lastResult.stats,
            }}
          />

          <div className="space-y-2">
            <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
              Overlays
            </h3>
            <ToolRow
              icon={<Radar size={14} />}
              label="Raw SAR backscatter"
              hint="The grayscale physics behind the detection"
              active={backscatterOn}
              loading={busy === "backscatter"}
              error={errors.backscatter}
              onClick={toggleBackscatter}
            />
            <ToolRow
              icon={<ImageIcon size={14} />}
              label="Optical (Sentinel-2)"
              hint="True-color context, cloud permitting"
              active={opticalOn}
              loading={busy === "optical"}
              error={errors.optical}
              onClick={toggleOptical}
            />
          </div>

          <div className="space-y-2">
            <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
              Time &amp; change
            </h3>
            <ToolRow
              icon={<GitCompareArrows size={14} />}
              label="Before / after compare"
              hint="Cross-fade pre- and post-event composites"
              active={!!compare}
              loading={busy === "compare"}
              error={errors.compare}
              onClick={toggleCompare}
            />
            <ToolRow
              icon={<Timer size={14} />}
              label="Time-series"
              hint="Scrub the metric across recent weeks"
              active={!!timeline}
              loading={busy === "timeline"}
              error={errors.timeline}
              onClick={toggleTimeline}
            />
          </div>

          <div className="space-y-2">
            <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
              Human impact
            </h3>
            <ToolRow
              icon={<UsersRound size={14} />}
              label="Population density"
              hint="GHSL heatmap of where people live"
              active={populationOn}
              loading={busy === "population"}
              error={errors.population}
              onClick={togglePopulation}
            />
            <button
              onClick={runImpact}
              disabled={busy === "impact"}
              className="w-full flex items-center gap-2.5 rounded-xl ring-1 ring-line bg-bg/70 px-3 py-2.5 text-left text-dim hover:text-ink transition disabled:opacity-60"
              title="People and built-up area inside the detection footprint"
            >
              <span className="text-dim">
                {busy === "impact" ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Users size={14} />
                )}
              </span>
              <span className="min-w-0">
                <span className="block text-xs text-ink">
                  Estimate people affected
                </span>
                <span className="block text-[10px] text-dim leading-tight">
                  Population &amp; built-up area in the footprint
                </span>
              </span>
            </button>
            {errors.impact && (
              <p className="text-[10px] text-amber leading-snug px-1">
                {errors.impact}
              </p>
            )}
            {impact && (
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-3">
                  <div className="flex items-center gap-1.5 font-mono text-[9px] tracking-[0.15em] text-dim uppercase">
                    <Users size={11} /> People
                  </div>
                  <div className="mt-1 font-display text-2xl text-teal leading-none">
                    {impact.population_affected.toLocaleString()}
                  </div>
                </div>
                <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-3">
                  <div className="flex items-center gap-1.5 font-mono text-[9px] tracking-[0.15em] text-dim uppercase">
                    <Building2 size={11} /> Built-up
                  </div>
                  <div className="mt-1 font-display text-2xl text-teal leading-none">
                    {impact.built_up_km2.toLocaleString()}
                    <span className="ml-1 text-xs text-dim">km²</span>
                  </div>
                </div>
                <p className="col-span-2 text-[10px] text-dim leading-snug">
                  Inside the detection footprint · GHSL 2020 · figures are
                  modelled estimates.
                </p>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
              Monitor
            </h3>
            <button
              onClick={watchArea}
              disabled={busy === "watch" || watched || !user || !alertsAvailable()}
              className={`w-full flex items-center gap-2.5 rounded-xl ring-1 px-3 py-2.5 text-left transition disabled:opacity-60 ${
                watched
                  ? "bg-raised text-teal ring-teal/50"
                  : "bg-bg/70 text-dim ring-line hover:text-ink"
              }`}
              title={
                !user
                  ? "Sign in to watch areas for new passes"
                  : "Re-check this area on future Sentinel-1 passes"
              }
            >
              <span className={watched ? "text-teal" : "text-dim"}>
                {busy === "watch" ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : watched ? (
                  <Check size={14} />
                ) : (
                  <Bell size={14} />
                )}
              </span>
              <span className="min-w-0">
                <span className="block text-xs text-ink">
                  {watched ? "Watching this area" : "Watch this area"}
                </span>
                <span className="block text-[10px] text-dim leading-tight">
                  {!user
                    ? "Sign in to enable alerts"
                    : "Alert on the next Sentinel-1 pass"}
                </span>
              </span>
            </button>
            {errors.watch && (
              <p className="text-[10px] text-amber leading-snug px-1">
                {errors.watch}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
              Export &amp; share
            </h3>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() =>
                  exportSrc &&
                  guard("geotiff", () => downloadGeoTIFF(exportSrc))
                }
                disabled={busy === "geotiff"}
                className="h-9 rounded-xl text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition disabled:opacity-50"
                title="Download the result raster as a GeoTIFF"
              >
                {busy === "geotiff" ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Download size={12} />
                )}
                GeoTIFF
              </button>
              <button
                onClick={() =>
                  exportSrc && guard("report", () => downloadReport(exportSrc))
                }
                disabled={busy === "report"}
                className="h-9 rounded-xl text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition disabled:opacity-50"
                title="Download a methodology report (markdown)"
              >
                {busy === "report" ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <FileText size={12} />
                )}
                Report
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={copyShare}
                className="h-9 rounded-xl text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition"
                title="Copy a reproducible link to this analysis"
              >
                {copied ? (
                  <Check size={12} className="text-teal" />
                ) : (
                  <Share2 size={12} />
                )}
                {copied ? "Copied" : "Share link"}
              </button>
              <button
                onClick={copyEmbed}
                className="h-9 rounded-xl text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim hover:text-ink transition"
                title="Copy an <iframe> snippet to embed this live result"
              >
                {embedCopied ? (
                  <Check size={12} className="text-teal" />
                ) : (
                  <Code2 size={12} />
                )}
                {embedCopied ? "Copied" : "Embed code"}
              </button>
            </div>
            {(errors.geotiff || errors.report) && (
              <p className="text-[10px] text-amber leading-snug px-1">
                {errors.geotiff || errors.report}
              </p>
            )}
          </div>
        </>
      )}
    </motion.aside>
  );
}

function ToolRow({
  icon,
  label,
  hint,
  active,
  loading,
  error,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  hint: string;
  active: boolean;
  loading: boolean;
  error?: string;
  onClick: () => void;
}) {
  return (
    <div className="space-y-1">
      <button
        onClick={onClick}
        disabled={loading}
        className={`w-full flex items-center gap-2.5 rounded-xl ring-1 px-3 py-2.5 text-left transition ${
          active
            ? "bg-raised text-teal ring-teal/50"
            : "bg-bg/70 text-dim ring-line hover:text-ink"
        } disabled:opacity-60`}
      >
        <span className={active ? "text-teal" : "text-dim"}>
          {loading ? <Loader2 size={14} className="animate-spin" /> : icon}
        </span>
        <span className="min-w-0">
          <span className="block text-xs text-ink">{label}</span>
          <span className="block text-[10px] text-dim leading-tight truncate">
            {hint}
          </span>
        </span>
        <span
          className={`ml-auto font-mono text-[9px] tracking-wider ${
            active ? "text-teal" : "text-dim"
          }`}
        >
          {active ? "ON" : "OFF"}
        </span>
      </button>
      {error && <p className="text-[10px] text-amber leading-snug px-1">{error}</p>}
    </div>
  );
}
