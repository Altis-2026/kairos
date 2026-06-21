/**
 * Research tools — extra ways to interrogate the latest analysis result:
 *   • Raw SAR backscatter (grayscale physics, not just the binary mask)
 *   • Sentinel-2 optical (true-color context)
 *   • Before/After comparison (cross-fade slider)
 *   • Time-series (scrub/animate the metric over time)
 *
 * Each acts on mapStore.lastResult, so it works whether the result came from
 * the wizard, the chat, or the quick-analysis pin.
 */
import { useState } from "react";
import { motion } from "framer-motion";
import {
  GitCompareArrows,
  Image as ImageIcon,
  Loader2,
  Radar,
  Timer,
  X,
} from "lucide-react";
import { useMapStore } from "../../stores/mapStore";
import {
  fetchBackscatter,
  fetchCompare,
  fetchOptical,
  fetchTimeSeries,
  type AnalysisRef,
} from "../../api/research";

const BACKSCATTER_ID = "research-backscatter";
const OPTICAL_ID = "research-optical";

export default function ResearchPanel({ onClose }: { onClose: () => void }) {
  const lastResult = useMapStore((s) => s.lastResult);
  const layers = useMapStore((s) => s.layers);
  const compare = useMapStore((s) => s.compare);
  const timeline = useMapStore((s) => s.timeline);

  const [busy, setBusy] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const ref: AnalysisRef | null = lastResult
    ? {
        analysis_type: lastResult.analysisType,
        bbox: lastResult.bbox,
        start_date: lastResult.startDate,
        end_date: lastResult.endDate,
      }
    : null;

  const backscatterOn = layers.some((l) => l.id === BACKSCATTER_ID);
  const opticalOn = layers.some((l) => l.id === OPTICAL_ID);

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
      className="absolute right-20 top-1/2 -translate-y-1/2 z-30 w-80 rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
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
          Run an analysis first — from the sidebar, the chat, or the ⚡ quick-pin.
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
