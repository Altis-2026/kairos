import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Eye,
  Loader2,
  Pickaxe,
  Radar,
  Shield,
  Ship,
  TreePine,
  Droplets,
  Check,
  Flag,
  SkipForward,
  X,
} from "lucide-react";
import Globe from "../Globe";
import { useMapStore } from "../../stores/mapStore";
import { runAnalyze } from "../../api/analyze";
import { applyResultToGlobe } from "../../lib/applyResult";
import { GUARDIAN_ZONES, type GuardianZone } from "../../lib/guardianZones";
import { goToApp } from "../../lib/embed";
import {
  loadFindings,
  patrolStats,
  saveFinding,
  type Finding,
  type Verdict,
} from "../../lib/patrol";
import type { AnalysisResult } from "../../types/analysis";

const THREAT_ICON = {
  mining: Pickaxe,
  logging: TreePine,
  fishing: Ship,
  spill: Droplets,
} as const;

function recentWindow(): { start_date: string; end_date: string } {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 45);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { start_date: iso(start), end_date: iso(end) };
}

export default function Guardian() {
  const home = `${location.origin}${location.pathname}#app`;
  const [selected, setSelected] = useState<GuardianZone | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [note, setNote] = useState("");
  const [findings, setFindings] = useState<Finding[]>(() => loadFindings());

  const stats = useMemo(() => patrolStats(findings), [findings]);

  function pickZone(z: GuardianZone) {
    setSelected(z);
    setResult(null);
    setError(null);
    setNote("");
    useMapStore.getState().requestFlyTo(z.center, 9);
  }

  async function scan() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const win = recentWindow();
      const res = await runAnalyze({
        analysis_type: selected.analysisType,
        bbox: selected.bbox,
        start_date: win.start_date,
        end_date: win.end_date,
      });
      setResult(res);
      applyResultToGlobe(res);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "No Sentinel-1 data for this zone right now. Try another zone."
      );
    } finally {
      setBusy(false);
    }
  }

  function submit(verdict: Verdict) {
    if (!selected || !result) return;
    const next = saveFinding({
      zoneId: selected.id,
      zoneName: selected.name,
      country: selected.country,
      analysisType: selected.analysisType,
      metricLabel: result.headline_stat.label,
      metricValue: result.headline_stat.value,
      metricUnit: result.headline_stat.unit,
      dataDate: result.data_date,
      verdict,
      note: note.trim() || undefined,
    });
    setFindings(next);
    setResult(null);
    setNote("");
  }

  return (
    <div className="relative h-full w-full bg-bg overflow-hidden">
      <Globe />

      <div className="absolute left-5 top-5 z-30 rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel px-4 py-2.5">
        <div className="flex items-center gap-2.5">
          <Shield size={16} className="text-teal" />
          <div>
            <div className="font-display text-lg text-ink leading-none">
              Kairos <span className="text-teal">Guardian</span>
            </div>
            <div className="font-mono text-[10px] tracking-[0.18em] text-dim mt-0.5">
              HELP SPOT ILLEGAL ACTIVITY FROM SPACE
            </div>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2">
          <Stat label="Reviewed" value={stats.reviewed} />
          <Stat label="Flagged" value={stats.flagged} accent />
          <Stat label="Zones" value={stats.zones} />
        </div>
      </div>

      <aside className="absolute right-5 top-5 z-30 w-80 max-h-[88vh] rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-3 overflow-hidden flex flex-col">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
            WATCH ZONES
          </span>
          <a href={home} onClick={goToApp} className="text-dim hover:text-ink" title="Exit Guardian">
            <X size={15} />
          </a>
        </div>

        <ul className="space-y-1.5 overflow-y-auto">
          {GUARDIAN_ZONES.map((z) => {
            const Icon = THREAT_ICON[z.threat];
            const active = selected?.id === z.id;
            return (
              <li key={z.id}>
                <button
                  onClick={() => pickZone(z)}
                  className={`w-full text-left rounded-xl bg-bg/70 ring-1 p-2.5 transition ${
                    active ? "ring-teal/60" : "ring-line hover:ring-teal/40"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Icon size={14} className="shrink-0 text-amber" />
                    <span className="text-[12px] text-ink truncate">{z.name}</span>
                    <span className="ml-auto font-mono text-[9px] text-dim">
                      {z.country}
                    </span>
                  </div>
                  <div className="text-[10px] text-dim mt-1 leading-snug">
                    {z.watchingFor}
                  </div>
                </button>
              </li>
            );
          })}
        </ul>

        {findings.length > 0 && (
          <div className="pt-2 border-t border-line">
            <div className="font-mono text-[9px] tracking-[0.2em] text-dim mb-1.5">
              RECENT FINDINGS
            </div>
            <ul className="space-y-1 max-h-32 overflow-y-auto">
              {findings.slice(0, 6).map((f) => (
                <li
                  key={f.id}
                  className="flex items-center gap-2 text-[10px] text-dim"
                >
                  {f.verdict === "flagged" ? (
                    <Flag size={10} className="text-amber shrink-0" />
                  ) : f.verdict === "natural" ? (
                    <Check size={10} className="text-teal shrink-0" />
                  ) : (
                    <SkipForward size={10} className="shrink-0" />
                  )}
                  <span className="truncate">{f.zoneName}</span>
                  <span className="ml-auto font-mono">
                    {f.metricValue}
                    {f.metricUnit}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <a
          href={home}
          onClick={goToApp}
          className="mt-auto block text-center h-9 rounded-xl text-xs ring-1 ring-line text-dim hover:text-teal hover:ring-teal/40 transition leading-9"
        >
          Open the full Kairos workspace →
        </a>
      </aside>

      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            className="absolute left-5 bottom-5 z-40 w-[22rem] rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-3"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h2 className="font-display text-base text-ink leading-tight">
                  {selected.name}
                </h2>
                <div className="font-mono text-[9px] tracking-[0.15em] text-amber uppercase mt-0.5">
                  {selected.country} · {selected.threat}
                </div>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="text-dim hover:text-ink"
                title="Close"
              >
                <X size={15} />
              </button>
            </div>

            <p className="text-[11px] text-dim leading-relaxed">{selected.brief}</p>

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
                  {result.display_name} · {result.data_date}
                </div>
              </div>
            )}

            {error && (
              <p className="text-[10px] text-amber leading-snug px-1">{error}</p>
            )}

            {!result ? (
              <button
                onClick={scan}
                disabled={busy}
                className="w-full h-10 rounded-xl bg-amber text-bg font-medium text-sm flex items-center justify-center gap-2 hover:brightness-110 transition disabled:opacity-60"
              >
                {busy ? (
                  <Loader2 size={15} className="animate-spin" />
                ) : (
                  <Radar size={15} />
                )}
                Scan this zone
              </button>
            ) : (
              <div className="space-y-2.5">
                <div className="flex items-center gap-1.5 text-[11px] text-ink">
                  <Eye size={13} className="text-teal" />
                  Your call: does this look like real activity?
                </div>
                <input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Add a note (optional)…"
                  className="w-full h-9 px-3 rounded-xl bg-bg/70 ring-1 ring-line text-[11px] text-ink placeholder-dim outline-none focus:ring-teal/50 transition"
                />
                <div className="grid grid-cols-3 gap-2">
                  <ReviewButton
                    onClick={() => submit("flagged")}
                    icon={<Flag size={13} />}
                    label="Flag"
                    tone="amber"
                  />
                  <ReviewButton
                    onClick={() => submit("natural")}
                    icon={<Check size={13} />}
                    label="Natural"
                    tone="teal"
                  />
                  <ReviewButton
                    onClick={() => submit("skip")}
                    icon={<SkipForward size={13} />}
                    label="Skip"
                    tone="dim"
                  />
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div className="rounded-lg bg-bg/70 ring-1 ring-line px-2 py-1.5 text-center">
      <div
        className={`font-display text-lg leading-none ${
          accent ? "text-amber" : "text-teal"
        }`}
      >
        {value}
      </div>
      <div className="font-mono text-[8px] tracking-[0.15em] text-dim uppercase mt-0.5">
        {label}
      </div>
    </div>
  );
}

function ReviewButton({
  onClick,
  icon,
  label,
  tone,
}: {
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  tone: "amber" | "teal" | "dim";
}) {
  const ring =
    tone === "amber"
      ? "hover:ring-amber/60 hover:text-amber"
      : tone === "teal"
      ? "hover:ring-teal/60 hover:text-teal"
      : "hover:ring-line hover:text-ink";
  return (
    <button
      onClick={onClick}
      className={`h-9 rounded-xl text-[11px] flex items-center justify-center gap-1.5 ring-1 ring-line text-dim transition ${ring}`}
    >
      {icon}
      {label}
    </button>
  );
}
