/**
 * Dark-vessel screening — radar ship detections matched against AIS broadcasts.
 *
 * Ship detection alone finds bright returns on water. Fusing those with the
 * transponder record is what turns them into maritime domain awareness: the
 * interesting object is the radar return with no matching broadcast. The
 * caveats are shown with the result, not buried, because an unmatched return
 * is a screening lead and not evidence of anything.
 */
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, Loader2, Play, Radio, Ship, X } from "lucide-react";
import { useMapStore, bboxCenterZoom } from "../../stores/mapStore";
import {
  listVesselCases,
  screenCase,
  type ScreenResult,
  type VesselCase,
} from "../../api/vessels";
import { panelShell } from "../../lib/responsive";

const MATCHED_LAYER = "vessels-broadcasting";
const DARK_LAYER = "vessels-unmatched";

export default function VesselPanel({ onClose }: { onClose: () => void }) {
  const [cases, setCases] = useState<VesselCase[] | null>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ScreenResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listVesselCases()
      .then((d) => setCases(d.cases))
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Could not load the cases.")
      );
  }, []);

  async function run(c: VesselCase) {
    if (running) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await screenCase(c.id);
      setResult(res);
      const map = useMapStore.getState();
      map.addRasterLayer({
        id: "vessels-radar",
        name: "Radar returns",
        tileUrl: res.tile_url,
        opacity: 0.85,
        visible: true,
        color: "#E8A318",
      });
      map.addPointLayer({
        id: MATCHED_LAYER,
        name: "Broadcasting vessels",
        data: res.matched,
        color: "#00BFA8",
        visible: true,
      });
      map.addPointLayer({
        id: DARK_LAYER,
        name: "No matching transponder",
        data: res.unmatched,
        color: "#FF3B5C",
        visible: true,
      });
      map.setAoi(c.bbox);
      const { center, zoom } = bboxCenterZoom(c.bbox);
      map.requestFlyTo(center, zoom);
    } catch (e) {
      setError(e instanceof Error ? e.message : "The screening failed to run.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <motion.aside
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`${panelShell(
        "lg:right-20 lg:left-auto lg:top-1/2 lg:-translate-y-1/2 lg:w-[22rem] lg:max-h-[78vh] lg:overflow-y-auto"
      )} space-y-4`}
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-dim">
          <Ship size={13} className="text-teal" /> DARK VESSELS
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      <p className="text-xs text-dim leading-relaxed">
        Big ships are supposed to broadcast their position over AIS radio.
        Radar sees every ship regardless. Line the two up and the gap is
        interesting: a bright radar return with no transponder nearby.
      </p>

      {!cases && !error && (
        <div className="flex items-center gap-2 text-xs text-dim">
          <Loader2 size={14} className="animate-spin" /> Loading cases…
        </div>
      )}

      {cases?.map((c) => (
        <div key={c.id} className="rounded-xl bg-bg/70 ring-1 ring-line p-3 space-y-2">
          <div>
            <div className="text-sm text-ink font-medium">{c.name}</div>
            <div className="font-mono text-[10px] text-dim mt-0.5">
              {c.region} · {c.target_date}
            </div>
          </div>
          <p className="text-[11px] text-dim leading-relaxed">{c.why}</p>
          {c.available ? (
            <button
              onClick={() => run(c)}
              disabled={running}
              className="w-full h-9 rounded-lg bg-amber text-bg text-xs font-medium hover:brightness-110 transition disabled:opacity-60 flex items-center justify-center gap-1.5"
            >
              {running ? (
                <>
                  <Loader2 size={12} className="animate-spin" /> Matching radar
                  to transponders…
                </>
              ) : (
                <>
                  <Play size={12} /> Run the screening
                </>
              )}
            </button>
          ) : (
            <p className="text-[10px] text-amber leading-snug rounded-lg bg-bg ring-1 ring-line p-2">
              AIS record not installed on this server. Run{" "}
              <span className="font-mono">tools/get_ais_case.py</span> to
              download the day from MarineCadastre.
            </p>
          )}
          <a
            href={c.ais_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-[10px] text-teal hover:underline"
          >
            AIS source: {c.ais_source} <ExternalLink size={9} />
          </a>
        </div>
      ))}

      {result && (
        <>
          <div className="rounded-xl bg-bg/70 ring-1 ring-teal/30 p-3">
            <div className="font-mono text-[10px] tracking-[0.18em] text-dim uppercase">
              {result.headline_stat.label}
            </div>
            <div className="mt-1 font-display text-3xl text-[#FF3B5C]">
              {result.unmatched_count}
              <span className="ml-1.5 text-base text-dim">
                {result.headline_stat.unit}
              </span>
            </div>
            <div className="mt-2 space-y-1 font-mono text-[10px] text-dim">
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-teal" />
                {result.matched_count} matched a transponder
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-[#FF3B5C]" />
                {result.unmatched_count} did not
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3 space-y-1 font-mono text-[10px] text-dim">
            <div className="flex items-center gap-1.5 text-teal">
              <Radio size={11} /> HOW THE MATCH WAS MADE
            </div>
            <div>Radar pass: {result.radar_time_utc}</div>
            <div>
              AIS window: {result.ais_window?.from} to {result.ais_window?.to}
            </div>
            <div>{result.ais_vessels_in_window} vessels broadcasting nearby</div>
            <div>
              Match radius {result.match_radius_m.base} m plus ship drift,
              typically {result.match_radius_m.typical} m
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="font-mono text-[10px] tracking-[0.18em] text-amber uppercase">
              Read this carefully
            </div>
            {result.caveats.map((c, i) => (
              <p key={i} className="text-[11px] text-dim leading-snug">
                {c}
              </p>
            ))}
          </div>
        </>
      )}

      {error && <p className="text-[11px] text-amber leading-snug">{error}</p>}
    </motion.aside>
  );
}
