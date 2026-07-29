import { useState } from "react";
import { motion } from "framer-motion";
import {
  Building2,
  Flame,
  Home,
  Loader2,
  MapPin,
  Telescope,
  TrendingDown,
  Waves,
  X,
} from "lucide-react";
import { useMapStore, bboxCenterZoom } from "../../stores/mapStore";
import { type PlaceHit } from "../../api/myplace";
import { runAnalyze } from "../../api/analyze";
import { applyResultToGlobe } from "../../lib/applyResult";
import { plainSentence } from "../../lib/plain";
import PlaceSearch from "../PlaceSearch";
import type { AnalysisResult } from "../../types/analysis";

const STORAGE_KEY = "kairos_myplace";

const CHECKS = [
  { type: "flood_extent", label: "Flooding", icon: Waves, days: 30 },
  { type: "wildfire_burn_scar", label: "Fire damage", icon: Flame, days: 60 },
  { type: "urban_growth", label: "New construction", icon: Building2, days: 90 },
  { type: "land_subsidence", label: "Sinking ground", icon: TrendingDown, days: 180 },
];

type CheckState = "pending" | "running" | "ok" | "none" | "failed";

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function loadSaved(): PlaceHit | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PlaceHit) : null;
  } catch {
    return null;
  }
}

export default function MyPlacePanel({ onClose }: { onClose: () => void }) {
  const [place, setPlace] = useState<PlaceHit | null>(() => loadSaved());
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [states, setStates] = useState<Record<string, CheckState>>({});
  const [results, setResults] = useState<Record<string, AnalysisResult>>({});
  const [scanning, setScanning] = useState(false);

  function adopt(hit: PlaceHit) {
    if (!hit.found || !hit.bbox) {
      setError("That address did not match anywhere. Try adding a city or ZIP.");
      return;
    }
    setPlace(hit);
    setStates({});
    setResults({});
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(hit));
    } catch {
      return;
    }
    const map = useMapStore.getState();
    map.setAoi(hit.bbox);
    const { center } = bboxCenterZoom(hit.bbox);
    map.requestFlyTo(center, 11.5);
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setError("This browser does not expose location.");
      return;
    }
    setLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        const lon = pos.coords.longitude;
        const lat = pos.coords.latitude;
        adopt({
          found: true,
          label: "Your current location",
          lon,
          lat,
          bbox: [
            +(lon - 0.06).toFixed(5),
            +(lat - 0.045).toFixed(5),
            +(lon + 0.06).toFixed(5),
            +(lat + 0.045).toFixed(5),
          ],
          source: "device location",
        });
      },
      () => {
        setLocating(false);
        setError("Location permission was denied. Type an address instead.");
      },
      { timeout: 10000 }
    );
  }

  async function scan() {
    if (!place?.found || !place.bbox || scanning) return;
    setScanning(true);
    setError(null);
    setResults({});
    setStates(Object.fromEntries(CHECKS.map((c) => [c.type, "pending"])));
    for (const check of CHECKS) {
      setStates((s) => ({ ...s, [check.type]: "running" }));
      try {
        const result = await runAnalyze({
          analysis_type: check.type,
          bbox: place.bbox,
          start_date: isoDaysAgo(check.days),
          end_date: isoDaysAgo(0),
        });
        applyResultToGlobe(result);
        setResults((r) => ({ ...r, [check.type]: result }));
        setStates((s) => ({
          ...s,
          [check.type]: result.headline_stat.value > 0 ? "ok" : "none",
        }));
      } catch {
        setStates((s) => ({ ...s, [check.type]: "failed" }));
      }
    }
    setScanning(false);
  }

  function openForesight() {
    if (!place?.bbox) return;
    const params = new URLSearchParams({
      bbox: place.bbox.join(","),
      label: place.label ?? "My place",
    });
    location.hash = `foresight&${params.toString()}`;
    location.reload();
  }

  function reset() {
    setPlace(null);
    setStates({});
    setResults({});
    setError(null);
    useMapStore.getState().setAoi(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      return;
    }
  }

  const finished = Object.values(states).filter(
    (s) => s === "ok" || s === "none" || s === "failed"
  ).length;
  const reportReady = !scanning && finished === CHECKS.length && finished > 0;
  const anyHits = Object.values(results).some(
    (r) => r.headline_stat.value > 0
  );

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[58dvh] sm:right-20 sm:top-1/2 sm:-translate-y-1/2 sm:w-80 sm:max-h-[82vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
          MY PLACE
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      {!place?.found ? (
        <>
          <p className="text-xs text-dim leading-relaxed">
            Type your address and Kairos reads the satellite record for your
            own neighborhood: recent flooding, fire damage, new construction
            and slow ground movement, in plain English.
          </p>
          <PlaceSearch
            ariaLabel="Your address"
            placeholder="Street, city or ZIP"
            onPick={(p) =>
              adopt({
                found: true,
                label: p.label,
                lon: p.lon,
                lat: p.lat,
                bbox: p.bbox,
                source: "map geocoder",
              })
            }
          />
          <button
            onClick={useMyLocation}
            disabled={locating}
            className="w-full flex items-center gap-2.5 rounded-xl ring-1 ring-line bg-bg/70 px-3 py-2.5 text-left text-dim hover:text-ink transition disabled:opacity-60"
          >
            <MapPin size={14} />
            <span className="text-xs text-ink">Use my location instead</span>
          </button>
          <p className="text-[10px] text-dim leading-snug">
            Addresses are only sent to a geocoder to find coordinates. Nothing
            is stored on a server.
          </p>
        </>
      ) : (
        <>
          <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-3">
            <div className="flex items-center gap-2">
              <Home size={14} className="text-teal shrink-0" />
              <span className="text-sm text-ink font-medium truncate">
                {place.label}
              </span>
            </div>
            <div className="mt-1 font-mono text-[10px] text-dim">
              about a 10 km circle around this point
            </div>
            <button
              onClick={reset}
              className="mt-1.5 text-[11px] text-dim hover:text-ink underline underline-offset-2"
            >
              Change place
            </button>
          </div>

          {!Object.keys(states).length && (
            <button
              onClick={scan}
              className="w-full h-10 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition"
            >
              Scan my neighborhood
            </button>
          )}

          {Object.keys(states).length > 0 && (
            <div className="space-y-2">
              {CHECKS.map((check) => {
                const st = states[check.type] ?? "pending";
                const res = results[check.type];
                return (
                  <div
                    key={check.type}
                    className={`flex items-start gap-2.5 rounded-xl ring-1 px-3 py-2.5 ${
                      st === "ok"
                        ? "bg-raised ring-teal/50"
                        : "bg-bg/70 ring-line"
                    }`}
                  >
                    <span
                      className={`mt-0.5 ${
                        st === "ok" ? "text-teal" : "text-dim"
                      }`}
                    >
                      {st === "running" ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <check.icon size={14} />
                      )}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-xs text-ink">
                        {check.label}
                      </span>
                      <span className="block text-[10px] text-dim leading-snug mt-0.5">
                        {st === "pending" && "Waiting..."}
                        {st === "running" && "Reading the radar archive..."}
                        {st === "failed" &&
                          "This check could not run here. Radar coverage gaps happen."}
                        {(st === "ok" || st === "none") &&
                          res &&
                          plainSentence(
                            check.type,
                            res.headline_stat.value,
                            res.data_date
                          )}
                      </span>
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {reportReady && (
            <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3 space-y-1.5">
              <div className="font-mono text-[10px] tracking-[0.18em] text-amber uppercase">
                The short version
              </div>
              <p className="text-[11px] text-dim leading-relaxed">
                {anyHits
                  ? "The satellites picked something up near you. The teal layers on the globe show exactly where; tap a check above for the plain reading."
                  : "Nothing unusual near you right now. No fresh flooding, fire damage or measurable ground movement in the recent record."}
              </p>
            </div>
          )}

          {reportReady && (
            <button
              onClick={openForesight}
              className="w-full h-10 rounded-xl ring-1 ring-line text-sm text-ink hover:ring-teal/50 transition flex items-center justify-center gap-2"
            >
              <Telescope size={14} />
              What could happen here? Open Foresight
            </button>
          )}
        </>
      )}

      {error && <p className="text-[11px] text-amber leading-snug">{error}</p>}
    </motion.aside>
  );
}
