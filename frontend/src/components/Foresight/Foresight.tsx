import { useEffect, useState } from "react";
import {
  ArrowLeft,
  CloudRain,
  Flame,
  Loader2,
  MapPin,
  Play,
  Telescope,
  TrendingDown,
  Waves,
} from "lucide-react";
import Globe from "../Globe";
import PlaceSearch from "../PlaceSearch";
import { useMapStore, bboxCenterZoom } from "../../stores/mapStore";
import { runForesight, type Hazard, type RiskOutlook } from "../../api/foresight";
import { HAZARD_NAMES, PLAYBOOKS } from "../../lib/preparedness";
import { goToApp } from "../../lib/embed";
import type { BBox } from "../../types/map";

const HAZARDS: { id: Hazard; icon: typeof Waves }[] = [
  { id: "flood", icon: Waves },
  { id: "wildfire", icon: Flame },
  { id: "drought", icon: CloudRain },
  { id: "subsidence", icon: TrendingDown },
];

const LEVEL_COLORS: Record<string, string> = {
  low: "text-teal",
  moderate: "text-amber",
  high: "text-[#FF7A3B]",
  "very high": "text-[#FF3B5C]",
};

const MONTH_LETTERS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

function parseHashTarget(): { bbox: BBox; label: string } | null {
  const hash = location.hash.replace(/^#/, "");
  if (!hash.startsWith("foresight")) return null;
  const qs = hash.replace(/^foresight&?/, "");
  const p = new URLSearchParams(qs);
  const bboxStr = p.get("bbox");
  if (!bboxStr) return null;
  const parts = bboxStr.split(",").map(Number);
  if (parts.length !== 4 || parts.some((n) => Number.isNaN(n))) return null;
  return {
    bbox: [parts[0], parts[1], parts[2], parts[3]] as BBox,
    label: p.get("label") ?? "Selected area",
  };
}

function plainTrend(outlook: RiskOutlook): string | null {
  if (!outlook.trend) return null;
  const mk = outlook.trend.mann_kendall;
  if (mk.trend === "increasing") {
    return `This is getting worse: a statistically significant rise (p=${mk.p_value}) across ${mk.n} years of data.`;
  }
  if (mk.trend === "decreasing") {
    return `This is easing: a statistically significant decline (p=${mk.p_value}) across ${mk.n} years of data.`;
  }
  return `No significant long-term trend across ${mk.n} years of data (p=${mk.p_value}); the year-to-year swings are within normal noise.`;
}

export default function Foresight() {
  const [target, setTarget] = useState<{ bbox: BBox; label: string } | null>(
    () => parseHashTarget()
  );
  const [hazard, setHazard] = useState<Hazard>("flood");
  const [running, setRunning] = useState(false);
  const [outlooks, setOutlooks] = useState<Partial<Record<Hazard, RiskOutlook>>>(
    {}
  );
  const [error, setError] = useState<string | null>(null);
  const [playbookOpen, setPlaybookOpen] = useState(false);

  const outlook = outlooks[hazard] ?? null;

  useEffect(() => {
    if (!target) return;
    const map = useMapStore.getState();
    map.setAoi(target.bbox);
    const { center, zoom } = bboxCenterZoom(target.bbox);
    map.requestFlyTo(center, Math.max(zoom, 8));
  }, [target]);

  function retarget(bbox: BBox, label: string) {
    setTarget({ bbox, label });
    setOutlooks({});
    setError(null);
    setPlaybookOpen(false);
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setError("This browser does not expose location.");
      return;
    }
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lon = pos.coords.longitude;
        const lat = pos.coords.latitude;
        retarget(
          [
            +(lon - 0.06).toFixed(5),
            +(lat - 0.045).toFixed(5),
            +(lon + 0.06).toFixed(5),
            +(lat + 0.045).toFixed(5),
          ],
          "Where I am now"
        );
      },
      () =>
        setError("Location permission was denied. Type a place instead."),
      { timeout: 10000 }
    );
  }

  function useMapView() {
    const vb = useMapStore.getState().viewportBbox;
    if (!vb) {
      setError("Move the map first, then try again.");
      return;
    }
    const spanLon = Math.min(vb[2] - vb[0], 2.5);
    const spanLat = Math.min(vb[3] - vb[1], 2.5);
    const cx = (vb[0] + vb[2]) / 2;
    const cy = (vb[1] + vb[3]) / 2;
    setTarget({
      bbox: [
        +(cx - spanLon / 2).toFixed(4),
        +(cy - spanLat / 2).toFixed(4),
        +(cx + spanLon / 2).toFixed(4),
        +(cy + spanLat / 2).toFixed(4),
      ],
      label: "Current map view",
    });
    setOutlooks({});
    setError(null);
  }

  async function run() {
    if (!target || running) return;
    setRunning(true);
    setError(null);
    setPlaybookOpen(false);
    try {
      const result = await runForesight(hazard, target.bbox);
      setOutlooks((o) => ({ ...o, [hazard]: result }));
      useMapStore.getState().addRasterLayer({
        id: "foresight-risk",
        name: `${HAZARD_NAMES[hazard]} outlook`,
        tileUrl: result.tile_url,
        opacity: 0.75,
        visible: true,
        color: "#E8A318",
      });
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "The outlook could not be computed."
      );
    } finally {
      setRunning(false);
    }
  }

  const months = outlook?.seasonal.months ?? [];
  const maxMonth = Math.max(...months, 0.0001);
  const playbook = PLAYBOOKS[hazard];

  return (
    <div className="relative h-full w-full bg-bg overflow-hidden">
      <Globe />

      <header className="absolute top-0 inset-x-0 z-40 flex items-center justify-between px-4 sm:px-6 h-14 bg-bg/70 backdrop-blur border-b border-line">
        <div className="flex items-center gap-3">
          <button
            onClick={goToApp}
            className="flex items-center gap-1.5 text-dim hover:text-ink transition-colors text-xs"
          >
            <ArrowLeft size={14} /> App
          </button>
          <span className="font-mono text-[10px] tracking-[0.24em] text-dim">
            KAIROS <span className="text-amber">FORESIGHT</span>
          </span>
        </div>
        <span className="hidden sm:block font-mono text-[10px] text-dim">
          measured history, honest odds, what to do about it
        </span>
      </header>

      <aside className="absolute z-30 max-lg:inset-x-3 max-lg:bottom-3 max-lg:top-[4.5rem] lg:left-5 lg:top-20 lg:bottom-5 lg:w-[380px] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4">
        {!target ? (
          <>
            <div className="flex items-center gap-2 text-teal">
              <Telescope size={16} />
              <h1 className="font-display text-lg text-ink">
                What could happen where you live?
              </h1>
            </div>
            <p className="text-xs text-dim leading-relaxed">
              Foresight reads decades of satellite records for one place and
              answers three questions: how exposed is it, when in the year does
              the risk peak, and is it getting worse. No simulation, just the
              measured record, with the receipts shown.
            </p>
            <PlaceSearch
              ariaLabel="Place to assess"
              onPick={(p) => retarget(p.bbox, p.label)}
            />
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={useMyLocation}
                className="h-10 rounded-xl ring-1 ring-line text-xs text-ink hover:ring-teal/50 transition flex items-center justify-center gap-1.5"
              >
                <MapPin size={13} /> My location
              </button>
              <button
                onClick={useMapView}
                className="h-10 rounded-xl ring-1 ring-line text-xs text-ink hover:ring-teal/50 transition"
              >
                This map view
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-3">
              <div className="text-sm text-ink font-medium truncate">
                {target.label}
              </div>
              <button
                onClick={() => {
                  setTarget(null);
                  setOutlooks({});
                }}
                className="mt-1 text-[11px] text-dim hover:text-ink underline underline-offset-2"
              >
                Change place
              </button>
            </div>

            <div className="grid grid-cols-4 gap-1.5">
              {HAZARDS.map((h) => {
                const done = outlooks[h.id];
                return (
                  <button
                    key={h.id}
                    onClick={() => {
                      setHazard(h.id);
                      setPlaybookOpen(false);
                    }}
                    className={`relative flex flex-col items-center gap-1 rounded-xl px-1 py-2.5 ring-1 transition ${
                      hazard === h.id
                        ? "bg-raised ring-teal/50 text-teal"
                        : "bg-bg/70 ring-line text-dim hover:text-ink"
                    }`}
                  >
                    <h.icon size={15} />
                    <span className="text-[9px] leading-tight text-center">
                      {HAZARD_NAMES[h.id]}
                    </span>
                    {done && (
                      <span
                        className={`absolute -top-1.5 -right-1 min-w-[18px] rounded-full bg-surface ring-1 ring-line px-1 font-mono text-[9px] ${
                          LEVEL_COLORS[done.level] ?? "text-ink"
                        }`}
                      >
                        {done.score}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {!outlook && (
              <button
                onClick={run}
                disabled={running}
                className="w-full h-11 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {running ? (
                  <>
                    <Loader2 size={15} className="animate-spin" />
                    Reading the satellite record...
                  </>
                ) : (
                  <>
                    <Play size={15} />
                    Compute {HAZARD_NAMES[hazard].toLowerCase()} outlook
                  </>
                )}
              </button>
            )}

            {!outlook && !running && (
              <p className="text-[10px] text-dim/80 leading-snug">
                This reads decades of satellite observations for the area, so it
                takes up to a minute. Results stay on each tab, so you can
                compare all four hazards.
              </p>
            )}

            {outlook && (
              <>
                <div className="rounded-xl bg-bg/70 ring-1 ring-line p-4 text-center">
                  <div className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
                    Exposure score
                  </div>
                  <div
                    className={`font-display text-5xl mt-1 ${
                      LEVEL_COLORS[outlook.level] ?? "text-ink"
                    }`}
                  >
                    {outlook.score}
                  </div>
                  <div
                    className={`mt-1 font-mono text-[11px] tracking-wide uppercase ${
                      LEVEL_COLORS[outlook.level] ?? "text-dim"
                    }`}
                  >
                    {outlook.level} exposure
                  </div>
                  <div className="mt-1.5 font-mono text-[9px] text-dim">
                    from the {outlook.data_years} record
                  </div>
                </div>

                <div className="space-y-1.5">
                  {outlook.drivers.map((d, i) => (
                    <p key={i} className="text-[11px] text-dim leading-relaxed">
                      {d}
                    </p>
                  ))}
                </div>

                {months.length === 12 && (
                  <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3">
                    <div className="font-mono text-[10px] tracking-[0.18em] text-dim uppercase mb-2">
                      When it happens
                    </div>
                    <div className="flex items-end gap-1 h-16">
                      {months.map((v, i) => (
                        <div key={i} className="flex-1 flex flex-col items-center gap-1">
                          <div
                            className={`w-full rounded-sm ${
                              v >= 0.6 * maxMonth && v > 0
                                ? "bg-amber"
                                : "bg-line"
                            }`}
                            style={{
                              height: `${Math.max(4, (v / maxMonth) * 52)}px`,
                            }}
                          />
                          <span className="font-mono text-[8px] text-dim">
                            {MONTH_LETTERS[i]}
                          </span>
                        </div>
                      ))}
                    </div>
                    {outlook.seasonal.peak_months.length > 0 && (
                      <p className="mt-2 text-[11px] text-teal leading-snug">
                        Peak season: {outlook.seasonal.peak_months.join(", ")}
                      </p>
                    )}
                  </div>
                )}

                {plainTrend(outlook) && (
                  <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3">
                    <div className="font-mono text-[10px] tracking-[0.18em] text-dim uppercase mb-1">
                      Is it getting worse?
                    </div>
                    <p className="text-[11px] text-dim leading-relaxed">
                      {plainTrend(outlook)}
                    </p>
                    <p className="mt-1 font-mono text-[9px] text-dim/70">
                      Mann-Kendall + OLS on {outlook.trend_label}
                    </p>
                  </div>
                )}

                {outlook.skill && (
                  <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-3">
                    <div className="font-mono text-[10px] tracking-[0.18em] text-teal uppercase mb-1">
                      Measured accuracy
                    </div>
                    <p className="text-[11px] text-dim leading-relaxed">
                      {Math.round(outlook.skill.hit_rate * 100)}% of the flood
                      extent independently mapped by the{" "}
                      {outlook.skill.reference} in this area falls inside the
                      zones marked here.
                    </p>
                    <p className="mt-1 text-[10px] text-dim/80 leading-snug">
                      {outlook.skill.note}
                    </p>
                  </div>
                )}

                <div className="rounded-xl bg-bg/70 ring-1 ring-line overflow-hidden">
                  <button
                    onClick={() => setPlaybookOpen((v) => !v)}
                    className="w-full px-3 py-2.5 flex items-center justify-between text-left"
                  >
                    <span className="font-mono text-[10px] tracking-[0.18em] text-amber uppercase">
                      What to do about it
                    </span>
                    <span className="text-dim text-xs">
                      {playbookOpen ? "hide" : "show"}
                    </span>
                  </button>
                  {playbookOpen && (
                    <div className="px-3 pb-3 space-y-2.5">
                      {(["before", "during", "after"] as const).map((phase) => (
                        <div key={phase}>
                          <div className="font-mono text-[9px] tracking-[0.2em] text-dim uppercase mb-1">
                            {phase}
                          </div>
                          <ul className="space-y-1">
                            {playbook[phase].map((tip, i) => (
                              <li
                                key={i}
                                className="text-[11px] text-dim leading-snug pl-3 relative before:content-[''] before:absolute before:left-0 before:top-[7px] before:h-1 before:w-1 before:rounded-full before:bg-teal"
                              >
                                {tip}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <p className="text-[10px] text-dim/80 leading-snug">
                  {outlook.method}
                </p>
              </>
            )}
          </>
        )}

        {error && <p className="text-[11px] text-amber leading-snug">{error}</p>}
      </aside>
    </div>
  );
}
