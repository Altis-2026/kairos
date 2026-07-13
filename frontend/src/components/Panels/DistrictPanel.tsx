import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Building2,
  Crosshair,
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
import type { AnalysisResult } from "../../types/analysis";

const STORAGE_KEY = "kairos_district";

const CHECKS = [
  { type: "flood_extent", label: "Flood check", icon: Waves, days: 30 },
  { type: "crop_monitoring", label: "Crop health", icon: Sprout, days: 30 },
  { type: "urban_growth", label: "Urban growth", icon: Building2, days: 60 },
  { type: "land_subsidence", label: "Subsidence", icon: TrendingDown, days: 120 },
];

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

  function useMyLocation() {
    if (!navigator.geolocation) {
      setError("This browser does not expose location.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        guard(() => locateDistrict(pos.coords.longitude, pos.coords.latitude)),
      () => {
        setLocating(false);
        setError("Location permission was denied. Try map center or manual entry.");
      },
      { timeout: 10000 }
    );
  }

  function useMapCenter() {
    const vb = useMapStore.getState().viewportBbox;
    if (!vb) {
      setError("Move the globe first, then try again.");
      return;
    }
    guard(() => locateDistrict((vb[0] + vb[2]) / 2, (vb[1] + vb[3]) / 2));
  }

  function useManual() {
    const st = stateInput.trim().toUpperCase();
    const num = numberInput.trim();
    if (st.length !== 2 || !num) {
      setError("Enter a two-letter state and a district number, like TX and 32.");
      return;
    }
    guard(() => lookupDistrict(st, num));
  }

  async function runCheck(check: (typeof CHECKS)[number]) {
    if (!district?.found || !district.bbox || running) return;
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
    } catch (e) {
      setError(e instanceof Error ? e.message : "That check failed to run.");
    } finally {
      setRunning(null);
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
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[58dvh] sm:right-20 sm:top-1/2 sm:-translate-y-1/2 sm:w-80 sm:max-h-[82vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
          MY DISTRICT
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      {!district?.found ? (
        <>
          <p className="text-xs text-dim leading-relaxed">
            Pick a US congressional district and Kairos becomes a standing
            radar dashboard for it: floods, crops, construction and ground
            movement inside the actual boundary.
          </p>

          <div className="space-y-2">
            <button
              onClick={useMyLocation}
              disabled={locating}
              className="w-full flex items-center gap-2.5 rounded-xl ring-1 ring-line bg-bg/70 px-3 py-2.5 text-left text-dim hover:text-ink transition disabled:opacity-60"
            >
              {locating ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <MapPin size={14} />
              )}
              <span className="text-xs text-ink">Use my location</span>
            </button>
            <button
              onClick={useMapCenter}
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
                placeholder="District, like 32 or AL"
                aria-label="District number"
                onKeyDown={(e) => e.key === "Enter" && useManual()}
                className="flex-1 h-10 rounded-xl bg-bg/70 ring-1 ring-line px-3 text-xs text-ink placeholder-dim outline-none focus:ring-amber/60"
              />
              <button
                onClick={useManual}
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
              <span className="text-sm text-ink font-medium truncate">
                {district.name}
              </span>
            </div>
            <div className="mt-1 font-mono text-[10px] text-dim">
              {district.label} · boundary drawn on the globe ·{" "}
              {district.vertex_count} points
            </div>
            <button
              onClick={reset}
              className="mt-1.5 text-[11px] text-dim hover:text-ink underline underline-offset-2"
            >
              Change district
            </button>
          </div>

          <div className="space-y-2">
            <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
              District checks
            </h3>
            {CHECKS.map((check) => {
              const done = results[check.type];
              return (
                <button
                  key={check.type}
                  onClick={() => runCheck(check)}
                  disabled={!!running}
                  className={`w-full flex items-center gap-2.5 rounded-xl ring-1 px-3 py-2.5 text-left transition disabled:opacity-60 ${
                    done
                      ? "bg-raised ring-teal/50"
                      : "bg-bg/70 ring-line hover:text-ink"
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
                  {done && (
                    <span className="font-mono text-[9px] text-teal shrink-0">
                      DONE
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <button
            onClick={makeBriefing}
            disabled={briefingBusy || !Object.keys(results).length}
            className="w-full h-10 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition disabled:opacity-40 flex items-center justify-center gap-2"
          >
            {briefingBusy ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <FileText size={14} />
            )}
            {Object.keys(results).length
              ? "Generate briefing"
              : "Run a check to enable the briefing"}
          </button>
          <p className="text-[10px] text-dim leading-snug">
            The briefing opens as a printable memo built from the checks you
            ran, ready to save as a PDF.
          </p>
        </>
      )}

      {error && (
        <p className="text-[11px] text-amber leading-snug">{error}</p>
      )}
    </motion.aside>
  );
}
