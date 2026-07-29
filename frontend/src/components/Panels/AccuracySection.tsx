import { useEffect, useState } from "react";
import { Loader2, Play, Target } from "lucide-react";
import {
  listBenchmarks,
  runBenchmark,
  type Benchmark,
  type BenchmarkResult,
} from "../../api/trust";
import { useMapStore, bboxCenterZoom } from "../../stores/mapStore";

export default function AccuracySection() {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, BenchmarkResult>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listBenchmarks()
      .then((d) => setBenchmarks(d.benchmarks))
      .catch(() => setBenchmarks([]));
  }, []);

  async function run(bm: Benchmark) {
    if (running) return;
    setRunning(bm.id);
    setError(null);
    try {
      const res = await runBenchmark(bm.id);
      setResults((r) => ({ ...r, [bm.id]: res }));
      const map = useMapStore.getState();
      map.addRasterLayer({
        id: `bench-kairos-${bm.id}`,
        name: `Kairos: ${bm.region}`,
        tileUrl: res.kairos_tile_url,
        opacity: 0.8,
        visible: true,
        color: "#00BFA8",
      });
      map.addRasterLayer({
        id: `bench-ref-${bm.id}`,
        name: `Reference: ${bm.reference}`,
        tileUrl: res.reference_tile_url,
        opacity: 0.55,
        visible: true,
        color: "#E8A318",
      });
      map.setAoi(bm.bbox);
      const { center, zoom } = bboxCenterZoom(bm.bbox);
      map.requestFlyTo(center, zoom);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Benchmark failed to run.");
    } finally {
      setRunning(null);
    }
  }

  if (!benchmarks.length) return null;

  return (
    <div className="space-y-2">
      <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
        Measured accuracy
      </h3>
      <p className="text-[10px] text-dim leading-snug">
        Re-runs the production detectors over historical disasters with
        independent reference maps and computes the overlap live. Slow (about
        a minute each); nothing is precomputed.
      </p>
      {benchmarks.map((bm) => {
        const res = results[bm.id];
        return (
          <div
            key={bm.id}
            className={`rounded-xl ring-1 p-3 space-y-1.5 ${
              res ? "bg-raised ring-teal/50" : "bg-bg/70 ring-line"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-[11px] text-ink leading-snug">
                {bm.region}
              </span>
              <button
                onClick={() => run(bm)}
                disabled={!!running}
                title="Run this benchmark against its reference map"
                className="shrink-0 h-7 w-7 grid place-items-center rounded-lg ring-1 ring-line text-dim hover:text-teal transition disabled:opacity-50"
              >
                {running === bm.id ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : res ? (
                  <Target size={12} className="text-teal" />
                ) : (
                  <Play size={12} />
                )}
              </button>
            </div>
            <div className="font-mono text-[9px] text-dim leading-snug">
              vs {bm.reference}
            </div>
            {res && (
              <>
                <div className="grid grid-cols-4 gap-1 pt-1">
                  {(["iou", "precision", "recall", "f1"] as const).map((k) => (
                    <div key={k} className="text-center">
                      <div className="font-display text-sm text-teal">
                        {res.metrics[k] !== null
                          ? (res.metrics[k] as number).toFixed(2)
                          : "n/a"}
                      </div>
                      <div className="font-mono text-[8px] text-dim uppercase">
                        {k}
                      </div>
                    </div>
                  ))}
                </div>
                <p className="text-[9px] text-dim/80 leading-snug">
                  Kairos {res.metrics.kairos_area_km2} km2 vs reference{" "}
                  {res.metrics.reference_area_km2} km2; both layers are now on
                  the globe (teal ours, amber reference).
                </p>
              </>
            )}
          </div>
        );
      })}
      {error && <p className="text-[10px] text-amber leading-snug">{error}</p>}
    </div>
  );
}
