import { X } from "lucide-react";
import { motion } from "framer-motion";
import { useSidebarStore } from "../../stores/sidebarStore";

export default function AnalyticsPanel({ onClose }: { onClose: () => void }) {
  const result = useSidebarStore((s) => s.result);

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[58dvh] sm:right-20 sm:top-1/2 sm:-translate-y-1/2 sm:w-80 sm:max-h-[82vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
          ANALYTICS
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      {!result ? (
        <p className="text-xs text-dim leading-relaxed">
          Run an analysis to see statistics here: headline measurement,
          confidence, and full data provenance.
        </p>
      ) : (
        <>
          <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-4">
            <div className="font-mono text-[10px] tracking-[0.18em] text-dim uppercase">
              {result.headline_stat.label}
            </div>
            <div className="mt-1 font-display text-3xl text-teal">
              {result.headline_stat.value.toLocaleString()}
              <span className="ml-1 text-base text-dim">
                {result.headline_stat.unit}
              </span>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs text-dim mb-1.5">
              <span>Confidence</span>
              <span className="font-mono text-teal">
                {Math.round(result.confidence * 100)}%
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-bg overflow-hidden ring-1 ring-line">
              <div
                className="h-full bg-teal"
                style={{ width: `${result.confidence * 100}%` }}
              />
            </div>
          </div>

          <ul className="space-y-1.5 text-xs">
            {Object.entries(result.stats)
              .filter(([, v]) => typeof v === "number" || typeof v === "string")
              .map(([k, v]) => (
                <li key={k} className="flex justify-between gap-3">
                  <span className="text-dim">{k.replaceAll("_", " ")}</span>
                  <span className="font-mono text-ink">{String(v)}</span>
                </li>
              ))}
          </ul>

          <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3 text-[11px] text-dim leading-relaxed">
            <span className="font-mono tracking-[0.15em] text-[9px] block mb-1">
              PROVENANCE
            </span>
            Sentinel-1 GRD (ESA Copernicus) · data date {result.data_date} ·
            Kairos pipeline v0.1 · {result.start_date} → {result.end_date}
          </div>
        </>
      )}
    </motion.aside>
  );
}
