import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Building2,
  Crosshair,
  Droplets,
  Flame,
  FileText,
  Landmark,
  Loader2,
  MapPin,
  Sprout,
  TrendingDown,
  Waves,
  X,
} from "lucide-react";
import { useMapStore, bboxCenterZoom } from "../../stores/mapStore";
import { locateDistrict, lookupDistrict, type District } from "../../api/districts";
import { runAnalyze } from "../../api/analyze";
import { applyResultToGlobe } from "../../lib/applyResult";
import { openBriefing } from "../../lib/exporters";
import { aoiAreaKm2 } from "../../lib/geo";
import { simulateHere } from "../../lib/loadSimulation";
import type { AnalysisResult } from "../../types/analysis";

const STORAGE_KEY = "kairos_district";

const CHECKS = [
  { type: "flood_extent", label: "Flooding", icon: Waves, days: 30 },
  { type: "wildfire_burn_scar", label: "Wildfire burn scars", icon: Flame, days: 60 },
  { type: "soil_moisture", label: "Drought and soil moisture", icon: Droplets, days: 30 },
  { type: "crop_monitoring", label: "Crop health", icon: Sprout, days: 30 },
  { type: "urban_growth", label: "New construction", icon: Building2, days: 90 },
  { type: "land_subsidence", label: "Sinking ground", icon: TrendingDown, days: 120 },
];

function centerBox(bbox: [number, number, number, number]): [number, number, number, number] {
  const cx = (bbox[0] + bbox[2]) / 2;
  const cy = (bbox[1] + bbox[3]) / 2;
  const half = 0.07;
  return [cx - half, cy - half, cx + half, cy + half];
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function loadSaved(): District | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as District) : null;
  } catch {
    return null;
  }
}

export default function DistrictPanel({ onClose }: { onClose: () => void }) {
  const [district, setDistrict] = useState<District | null>(() => loadSaved());
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stateInput, setStateInput] = useState("");
  const [numberInput, setNumberInput] = useState("");
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, AnalysisResult>>({});
  const [briefingBusy, setBriefingBusy] = useState(false);
  const [runningAll, setRunningAll] = useState(false);
  const [simBusy, setSimBusy] = useState<"flood" | "fire" | null>(null);

  useEffect(() => {
    if (district?.found && district.ring && district.bbox) {
      const map = useMapStore.getState();
      map.setAoiPolygon(district.ring);
      const { center, zoom } = bboxCenterZoom(district.bbox);
      map.requestFlyTo(center, zoom);
    }
  }, [district]);

  function adopt(d: District) {
    setError(null);
    if (!d.found) {
      setError(d.note ?? "No district found there.");
      return;
    }
    setDistrict(d);
    setResults({});
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(d));
    } catch {
      return;
    }
  }

  async function guard(fn: () => Promise<District>) {
    setLocating(true);
    setError(null);
    try {
      adopt(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "District lookup failed.");
    } finally {
      setLocating(false);
    }
  }

  function locateByDevice() {
    if (!navigator.geolocation) {
      setError("This browser does not expose location.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => guard(() => locateDistrict(pos.coords.longitude, pos.coords.latitude)),
      () => {
        setLocating(false);
        setError("Location permission was denied. Try map center or manual entry.");
      },
      { timeout: 10000 }
    );
  }

  function locateByMapCenter() {
    const vb = useMapStore.getState().viewportBbox;
    if (!vb) {
      setError("Move the globe first, then try again.");
      return;
    }
    guard(() => locateDistrict((vb[0] + vb[2]) / 2, (vb[1] + vb[3]) / 2));
  }

  function lookupManual() {
    const st = stateInput.trim().toUpperCase();
    const num = numberInput.trim();
    if (st.length !== 2 || !num) {
      setError("Enter a two-letter state and a district number, like TX and 26.");
      return;
    }
    guard(() => lookupDistrict(st, num));
  }

  async function runCheck(check: (typeof CHECKS)[number]): Promise<boolean> {
    if (!district?.found || !district.bbox) return false;
    setRunning(check.type);
    setError(null);
    try {
      const result = await runAnalyze({
        analysis_type: check.type,
        bbox: district.bbox,
        start_date: isoDaysAgo(check.days),
        end_date: isoDaysAgo(0),
        polygon: district.ring,
      });
      applyResultToGlobe(result);
      setResults((r) => ({ ...r, [check.type]: result }));
      return true;
    } catch (e) {
      setError(`${check.label}: ${e instanceof Error ? e.message : "the check failed to run."}`);
      return false;
    } finally {
      setRunning(null);
    }
  }

  async function runAll() {
    if (runningAll || running) return;
    setRunningAll(true);
    for (const check of CHECKS) {
      if (!results[check.type]) await runCheck(check);
    }
    setRunningAll(false);
  }

  async function simulate(kind: "flood" | "fire") {
    if (!district?.bbox || simBusy) return;
    setSimBusy(kind);
    setError(null);
    try {
      await simulateHere(kind, centerBox(district.bbox));
    } catch (e) {
      setError(e instanceof Error ? e.message : "The simulation failed.");
    } finally {
      setSimBusy(null);
    }
  }

  async function makeBriefing() {
    if (!district?.found || !district.bbox) return;
    const done = Object.values(results);
    if (!done.length) return;
    setBriefingBusy(true);
    setError(null);
    try {
      await openBriefing({
        area_name: district.name ?? "Selected district",
        area_label: district.label,
        area_km2: aoiAreaKm2(district.bbox, district.ring ?? null),
        prepared_for: `Office of ${district.label ?? "the district"}`,
        findings: done.map((r) => ({
          analysis_type: r.analysis_type,
          display_name: r.display_name,
          headline_label: r.headline_stat.label,
          headline_value: r.headline_stat.value,
          headline_unit: r.headline_stat.unit,
          data_date: r.data_date,
          start_date: r.start_date,
          end_date: r.end_date,
          confidence: r.confidence,
        })),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Briefing export failed.");
    } finally {
      setBriefingBusy(false);
    }
  }

  function reset() {
    setDistrict(null);
    setResults({});
    setError(null);
    useMapStore.getState().setAoi(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      return;
    }
  }

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[58dvh] sm:right-20 sm:top-20 sm:bottom-36 sm:w-80 overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim">MY DISTRICT</span>
        <button onClick={onClose} className="text-dim hover:text-ink" aria-label="Close" title="Close">
          <X size={15} />
        </button>
      </div>

      {!district?.found ? (
        <>
          <p className="text-xs text-dim leading-relaxed">
            Pick a US congressional district and Kairos becomes a standing radar dashboard for it: floods,
            crops, construction and ground movement inside the actual boundary.
          </p>

          <div className="space-y-2">
            <button
              onClick={locateByDevice}
              disabled={locating}
              className="w-full flex items-center gap-2.5 rounded-xl ring-1 ring-line bg-bg/70 px-3 py-2.5 text-left text-dim hover:text-ink transition disabled:opacity-60"
            >
              {locating ? <Loader2 size={14} className="animate-spin" /> : <MapPin size={14} />}
              <span className="text-xs text-ink">Use my location</span>
            </button>
            <button
              onClick={locateByMapCenter}
              disabled={locating}
              className="w-full flex items-center gap-2.5 rounded-xl ring-1 ring-line bg-bg/70 px-3 py-2.5 text-left text-dim hover:text-ink transition disabled:opacity-60"
            >
              <Crosshair size={14} />
              <span className="text-xs text-ink">Use the map center</span>
            </button>
            <div className="flex gap-2">
              <input
                value={stateInput}
                onChange={(e) => setStateInput(e.target.value)}
                placeholder="TX"
                maxLength={2}
                aria-label="State abbreviation"
                className="w-16 h-10 rounded-xl bg-bg/70 ring-1 ring-line px-3 text-xs text-ink placeholder-dim outline-none focus:ring-amber/60 uppercase"
              />
              <input
                value={numberInput}
                onChange={(e) => setNumberInput(e.target.value)}
                placeholder="District, like 26 or AL"
                aria-label="District number"
                onKeyDown={(e) => e.key === "Enter" && lookupManual()}
                className="flex-1 h-10 rounded-xl bg-bg/70 ring-1 ring-line px-3 text-xs text-ink placeholder-dim outline-none focus:ring-amber/60"
              />
              <button
                onClick={lookupManual}
                disabled={locating}
                className="h-10 px-3 rounded-xl bg-amber text-bg text-xs font-medium hover:brightness-110 transition disabled:opacity-50"
              >
                Go
              </button>
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-3">
            <div className="flex items-center gap-2">
              <Landmark size={14} className="text-teal shrink-0" />
              <span className="text-sm text-ink font-medium truncate">{district.name}</span>
            </div>
            <div className="mt-1 font-mono text-[10px] text-dim">
              {district.label} · boundary drawn on the globe · {district.vertex_count} points
            </div>
            <button
              onClick={reset}
              className="mt-1.5 text-[11px] text-dim hover:text-ink underline underline-offset-2"
            >
              Change district
            </button>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">District checks</h3>
              <button
                onClick={() => void runAll()}
                disabled={runningAll || !!running || Object.keys(results).length === CHECKS.length}
                className="text-[11px] text-teal hover:underline disabled:opacity-40 disabled:no-underline"
              >
                {runningAll ? "Running…" : "Run all"}
              </button>
            </div>
            {CHECKS.map((check) => {
              const done = results[check.type];
              return (
                <button
                  key={check.type}
                  onClick={() => void runCheck(check)}
                  disabled={!!running || runningAll}
                  className={`w-full flex items-center gap-2.5 rounded-xl ring-1 px-3 py-2.5 text-left transition disabled:opacity-60 ${
                    done ? "bg-raised ring-teal/50" : "bg-bg/70 ring-line hover:text-ink"
                  }`}
                >
                  <span className={done ? "text-teal" : "text-dim"}>
                    {running === check.type ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <check.icon size={14} />
                    )}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-xs text-ink">{check.label}</span>
                    <span className="block text-[10px] text-dim leading-tight">
                      {done
                        ? `${done.headline_stat.label}: ${done.headline_stat.value} ${done.headline_stat.unit}`
                        : `Last ${check.days} days inside the boundary`}
                    </span>
                  </span>
                  {done && <span className="font-mono text-[9px] text-teal shrink-0">DONE</span>}
                </button>
              );
            })}
          </div>

          <div className="space-y-2">
            <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">What if</h3>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => void simulate("flood")}
                disabled={!!simBusy}
                className="h-10 rounded-xl ring-1 ring-line bg-bg/70 text-xs text-ink flex items-center justify-center gap-1.5 hover:ring-teal/60 transition disabled:opacity-50"
              >
                {simBusy === "flood" ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Waves size={13} className="text-teal" />
                )}
                Simulate a flood
              </button>
              <button
                onClick={() => void simulate("fire")}
                disabled={!!simBusy}
                className="h-10 rounded-xl ring-1 ring-line bg-bg/70 text-xs text-ink flex items-center justify-center gap-1.5 hover:ring-ember/60 transition disabled:opacity-50"
              >
                {simBusy === "fire" ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Flame size={13} className="text-ember" />
                )}
                Simulate a wildfire
              </button>
            </div>
            <p className="text-[10px] text-dim leading-snug">
              Runs a physics model on real terrain near the district center. Results are simulations, not
              observations.
            </p>
          </div>

          <button
            onClick={makeBriefing}
            disabled={briefingBusy || !Object.keys(results).length}
            className="w-full h-10 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition disabled:opacity-40 flex items-center justify-center gap-2"
          >
            {briefingBusy ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
            {Object.keys(results).length ? "Generate briefing" : "Run a check to enable the briefing"}
          </button>
          <p className="text-[10px] text-dim leading-snug">
            The briefing opens as a printable memo built from the checks you ran, ready to save as a PDF.
          </p>
        </>
      )}

      {error && <p className="text-[11px] text-amber leading-snug">{error}</p>}
    </motion.aside>
  );
}
