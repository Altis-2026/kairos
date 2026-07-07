import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Waves,
  Ship,
  Flame,
  Droplets,
  Trees,
  Snowflake,
  Activity,
  Building,
  Building2,
  TrendingDown,
  Sprout,
  Pickaxe,
  Loader2,
  Zap,
  X,
  type LucideIcon,
} from "lucide-react";
import { fetchRegistry } from "../../api/registry";
import { runAnalyze } from "../../api/analyze";
import { useMapStore } from "../../stores/mapStore";
import { applyResultToGlobe } from "../../lib/applyResult";
import type { AnalysisType } from "../../types/analysis";

const ICONS: Record<string, LucideIcon> = {
  waves: Waves,
  ship: Ship,
  flame: Flame,
  droplets: Droplets,
  trees: Trees,
  snowflake: Snowflake,
  activity: Activity,
  building: Building,
  "building-2": Building2,
  "trending-down": TrendingDown,
  sprout: Sprout,
  pickaxe: Pickaxe,
};

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export default function QuickAnalysisPanel() {
  const aoi = useMapStore((s) => s.aoi);
  const close = () => useMapStore.getState().setQuickAnalysisOpen(false);

  const { data: tasks } = useQuery({
    queryKey: ["registry"],
    queryFn: fetchRegistry,
    staleTime: 5 * 60 * 1000,
  });

  const [selected, setSelected] = useState<string | null>(null);
  const [startDate, setStartDate] = useState(isoDaysAgo(30));
  const [endDate, setEndDate] = useState(isoDaysAgo(0));
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const center = useMemo(() => {
    if (!aoi) return null;
    return {
      lng: ((aoi[0] + aoi[2]) / 2).toFixed(2),
      lat: ((aoi[1] + aoi[3]) / 2).toFixed(2),
    };
  }, [aoi]);

  if (!aoi) return null;

  async function run() {
    if (!selected || !aoi || running) return;
    if (startDate >= endDate) {
      setError("Start date must be before end date.");
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const result = await runAnalyze({
        analysis_type: selected,
        bbox: aoi,
        start_date: startDate,
        end_date: endDate,
      });
      applyResultToGlobe(result);
      close();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Analysis failed. Try again."
      );
    } finally {
      setRunning(false);
    }
  }

  return (
    <motion.aside
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 24 }}
      className="absolute z-40 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[58dvh] sm:right-20 sm:top-20 sm:w-80 sm:max-h-[82vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-amber">
          <Zap size={12} /> QUICK ANALYSIS
        </span>
        <button onClick={close} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      {center && (
        <p className="font-mono text-[11px] text-dim">
          Pin · {center.lat}, {center.lng} · ~50 km box
        </p>
      )}

      <div className="grid grid-cols-2 gap-2">
        {(tasks ?? []).map((t: AnalysisType) => {
          const Icon = ICONS[t.icon] ?? Waves;
          const active = selected === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setSelected(t.id)}
              title={t.description}
              className={`flex items-center gap-2 h-10 px-2.5 rounded-lg text-xs ring-1 transition ${
                active
                  ? "bg-raised text-teal ring-teal/50"
                  : "text-dim ring-line hover:text-ink hover:ring-line"
              }`}
            >
              <Icon
                size={15}
                style={{ color: active ? undefined : t.color_palette[0] }}
                className="shrink-0"
              />
              <span className="truncate">{t.display_name.split(" ")[0]}</span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <label className="space-y-1">
          <span className="font-mono text-[9px] tracking-[0.18em] text-dim uppercase">
            From
          </span>
          <input
            type="date"
            value={startDate}
            max={endDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full h-9 px-2 rounded-lg bg-bg/70 ring-1 ring-line text-xs text-ink outline-none focus:ring-teal/50"
          />
        </label>
        <label className="space-y-1">
          <span className="font-mono text-[9px] tracking-[0.18em] text-dim uppercase">
            To
          </span>
          <input
            type="date"
            value={endDate}
            min={startDate}
            max={isoDaysAgo(0)}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full h-9 px-2 rounded-lg bg-bg/70 ring-1 ring-line text-xs text-ink outline-none focus:ring-teal/50"
          />
        </label>
      </div>

      {error && <p className="text-xs text-amber leading-relaxed">{error}</p>}

      <button
        onClick={run}
        disabled={!selected || running}
        className="w-full h-11 rounded-xl bg-amber text-bg font-medium text-sm hover:brightness-110 transition disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {running ? (
          <>
            <Loader2 size={16} className="animate-spin" /> Running…
          </>
        ) : (
          "Run analysis"
        )}
      </button>
    </motion.aside>
  );
}
