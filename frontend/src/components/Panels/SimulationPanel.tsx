/**
 * Forward simulation: pick a scene, run it, control how it draws.
 *
 * Two models share this panel — a flood routed over terrain and a wildfire
 * spread across it. They are presented together because they answer the same
 * shape of question ("what would happen here?") and differ from every other
 * analysis in Kairos in the same way: the terrain is measured and the event
 * is not. So the panel carries that statement once, prominently, and every
 * scene carries its own disclosure from the backend underneath it.
 *
 * Layers the viewer does not actually have yet are rendered as explicitly
 * disabled "soon" rows. A toggle that silently does nothing is worse than no
 * toggle at all — it implies the feature exists and is simply broken.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  CloudRain,
  Flame,
  Layers3,
  Loader2,
  MapPin,
  Mountain,
  Play,
  Share2,
  Waves,
  Wind,
  X,
} from "lucide-react";
import { fetchScenes, runSimulation, type SimulationScene } from "../../api/simulate";
import { useSimulationStore } from "../../stores/simulationStore";
import { useMapStore, bboxCenterZoom } from "../../stores/mapStore";
import { decodeSimulation, rampCss } from "../../lib/simulation";
import { burnRampCss, decodeFire } from "../../lib/fire";
import { panelShellFlex } from "../../lib/responsive";
import type { BBox } from "../../types/map";
import type { FirePayload, SimulationPayload } from "../../types/simulation";

/** Layers that are real features but not built yet — shown, never faked. */
const PLANNED_LAYERS = [
  { icon: CloudRain, label: "Rainfall", note: "Rain-on-grid forcing" },
  { icon: Share2, label: "Watershed", note: "Flow accumulation from the DEM" },
  { icon: MapPin, label: "Impact points", note: "Population & buildings at risk" },
];

/** Compass bearing to the eight-point name a person would actually say. */
function compass(bearing: number): string {
  const points = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return points[Math.round(((bearing % 360) + 360) % 360 / 45) % 8];
}

/** The one-line summary under a scene name, per model. */
function sceneSubtitle(scene: SimulationScene): string {
  if (scene.kind === "fire") {
    const wind = scene.wind_ms ?? 0;
    const from = compass(scene.wind_from_bearing ?? 0);
    return `${scene.region} · ${scene.fuel_model} · ${wind} m/s from ${from} · ${scene.duration_hours}h`;
  }
  const peak = scene.peak_discharge_m3s ?? 0;
  return `${scene.region} · ${peak.toLocaleString()} m³/s peak · ${scene.duration_hours}h`;
}

export default function SimulationPanel({ onClose }: { onClose: () => void }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["simulation-scenes"],
    queryFn: () => fetchScenes(),
    staleTime: 10 * 60 * 1000,
  });

  const sim = useSimulationStore((s) => s.sim);
  const fire = useSimulationStore((s) => s.fire);
  const status = useSimulationStore((s) => s.status);
  const simError = useSimulationStore((s) => s.error);
  const progressNote = useSimulationStore((s) => s.progressNote);
  const showFlood = useSimulationStore((s) => s.showFlood);
  const showTerrain = useSimulationStore((s) => s.showTerrain);
  const opacity = useSimulationStore((s) => s.opacity);
  const depthScaleM = useSimulationStore((s) => s.depthScaleM);
  const frontMinutes = useSimulationStore((s) => s.frontMinutes);

  const [activeScene, setActiveScene] = useState<string | null>(null);

  async function launch(scene: SimulationScene) {
    const store = useSimulationStore.getState();
    setActiveScene(scene.id);
    store.setStatus("running");
    store.setProgressNote("Fetching terrain…");
    try {
      const result = await runSimulation(
        { kind: scene.kind, scene: scene.id },
        (note) => useSimulationStore.getState().setProgressNote(note)
      );
      if (scene.kind === "fire") {
        store.setProgressNote("Decoding arrival times…");
        store.loadFire(decodeFire(result.simulation as FirePayload));
      } else {
        store.setProgressNote("Decoding frames…");
        store.loadSimulation(
          await decodeSimulation(result.simulation as SimulationPayload)
        );
      }

      const bbox = result.bbox as BBox;
      const { center, zoom } = bboxCenterZoom(bbox);
      // Pitched and rotated: a flood in a valley is unreadable from straight
      // above, and this is the view the terrain relief was turned on for.
      useMapStore.getState().requestFlyTo(center, zoom);
    } catch (e) {
      store.setStatus("error", e instanceof Error ? e.message : "Simulation failed.");
    } finally {
      setActiveScene(null);
    }
  }

  const running = status === "running";
  const scenes = data?.scenes ?? [];
  const floodScenes = scenes.filter((s) => s.kind !== "fire");
  const fireScenes = scenes.filter((s) => s.kind === "fire");

  return (
    <motion.aside
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      // panelShellFlex, not panelShell: this is the tallest panel in the app
      // once a simulation is loaded (scenes + disclosure + layers + two
      // sliders + legend + solver stats), and it has no natural cap. Without
      // an outer scroll region it just kept growing — on a 1600x800 window it
      // measured 1119px tall against an 800px viewport, hanging 160px off
      // BOTH the top and bottom, the bottom collision landing right on
      // Mapbox's attribution strip. lg:top-24/bottom-3 bounds it to the
      // viewport the same way every other tall panel in the app already does.
      className={panelShellFlex(
        "lg:right-20 lg:left-auto lg:top-24 lg:bottom-3 lg:w-[21rem]"
      )}
    >
      <div className="flex items-center justify-between mb-3 shrink-0">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
          FORWARD SIMULATION
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-0.5 -mr-0.5">
        {/* What this is — stated before anything can be run. */}
        <div className="rounded-xl bg-amber/[0.07] ring-1 ring-amber/30 px-3 py-2.5">
          <span className="inline-flex items-center gap-1.5 font-mono text-[9px] tracking-[0.18em] text-amber">
            <Waves size={10} />
            SIMULATED — NOT AN OBSERVATION
          </span>
          <p className="mt-1.5 text-[11px] text-dim leading-relaxed">
            Forward models over real Copernicus terrain: water routed by a
            shallow-water solver, fire spread by Rothermel behaviour. The
            ground is measured; the event is not, and neither is a forecast.
            For something that actually happened, run Flood Extent Mapping or
            Wildfire Burn Scar Mapping.
          </p>
        </div>

        {/* Scenes */}
        {isLoading && (
          <p className="font-mono text-xs text-teal">Loading scenes…</p>
        )}
        {isError && (
          <p className="text-[11px] text-amber leading-relaxed">
            Can't reach the simulation API.{" "}
            {error instanceof Error ? error.message : ""}
          </p>
        )}

        {floodScenes.length > 0 && (
          <div className="space-y-1.5">
            <h3 className="flex items-center gap-1.5 font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
              <Waves size={11} className="text-teal" />
              Showcase scenes
            </h3>
            <ul className="space-y-1.5">
              {floodScenes.map((scene) => (
                <li key={scene.id}>
                  <button
                    onClick={() => void launch(scene)}
                    disabled={running}
                    className="w-full text-left rounded-xl bg-bg/70 ring-1 ring-line px-3 py-2.5 transition hover:ring-teal/50 disabled:opacity-50 group"
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-xs text-ink truncate">{scene.name}</span>
                      <span className="ml-auto shrink-0 text-teal opacity-0 group-hover:opacity-100 transition-opacity">
                        {activeScene === scene.id ? (
                          <Loader2 size={13} className="animate-spin opacity-100" />
                        ) : (
                          <Play size={13} />
                        )}
                      </span>
                    </span>
                    <span className="block text-[10px] text-dim mt-0.5">
                      {sceneSubtitle(scene)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {fireScenes.length > 0 && (
          <div className="space-y-1.5">
            <h3 className="flex items-center gap-1.5 font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
              <Flame size={11} className="text-ember" />
              Wildfire scenes
            </h3>
            <ul className="space-y-1.5">
              {fireScenes.map((scene) => (
                <li key={scene.id}>
                  <button
                    onClick={() => void launch(scene)}
                    disabled={running}
                    className="w-full text-left rounded-xl bg-bg/70 ring-1 ring-line px-3 py-2.5 transition hover:ring-ember/50 disabled:opacity-50 group"
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-xs text-ink truncate">{scene.name}</span>
                      <span className="ml-auto shrink-0 text-ember opacity-0 group-hover:opacity-100 transition-opacity">
                        {activeScene === scene.id ? (
                          <Loader2 size={13} className="animate-spin opacity-100" />
                        ) : (
                          <Play size={13} />
                        )}
                      </span>
                    </span>
                    <span className="block text-[10px] text-dim mt-0.5">
                      {sceneSubtitle(scene)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <p className="text-[9px] text-dim leading-relaxed">
              Scenarios, not reconstructions. Each place has burned, but the
              fuel, wind and ignition are chosen — none of these reproduces an
              actual fire.
            </p>
          </div>
        )}

        {running && (
          <p className="flex items-center gap-2 font-mono text-[11px] text-teal">
            <Loader2 size={13} className="animate-spin" />
            {progressNote ?? "Solving…"}
          </p>
        )}
        {status === "error" && simError && (
          <p className="text-[11px] text-amber leading-relaxed">{simError}</p>
        )}

        {/* Display controls — only meaningful once something is loaded */}
        {sim && (
          <>
            <div className="space-y-1.5">
              <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
                Layers
              </h3>
              <LayerToggle
                icon={Waves}
                label="Flood depth"
                note="Modelled water surface"
                on={showFlood}
                onClick={() => useSimulationStore.getState().setShowFlood(!showFlood)}
              />
              <LayerToggle
                icon={Mountain}
                label="Terrain relief"
                note="3D elevation under the water"
                on={showTerrain}
                onClick={() => useSimulationStore.getState().setShowTerrain(!showTerrain)}
              />
              {PLANNED_LAYERS.map((l) => (
                <div
                  key={l.label}
                  className="w-full flex items-center gap-2.5 rounded-xl ring-1 ring-line/60 px-3 py-2.5 opacity-45 cursor-not-allowed"
                  title="Not built yet — this toggle is intentionally inert"
                >
                  <l.icon size={14} className="text-dim shrink-0" />
                  <span className="min-w-0">
                    <span className="block text-xs text-ink">{l.label}</span>
                    <span className="block text-[10px] text-dim leading-tight">
                      {l.note}
                    </span>
                  </span>
                  <span className="ml-auto font-mono text-[9px] tracking-wider text-dim">
                    SOON
                  </span>
                </div>
              ))}
            </div>

            <Slider
              label="Depth scale"
              value={depthScaleM}
              min={0.25}
              max={Math.max(sim.peakCm / 100, 0.5)}
              step={0.05}
              suffix=" m"
              onChange={(v) => useSimulationStore.getState().setDepthScaleM(v)}
            />
            <Slider
              label="Opacity"
              value={opacity}
              min={0.1}
              max={1}
              step={0.05}
              suffix=""
              format={(v) => `${Math.round(v * 100)}%`}
              onChange={(v) => useSimulationStore.getState().setOpacity(v)}
            />

            {/* Depth legend — the same ramp the pixels use */}
            <div className="space-y-1">
              <div
                className="h-2.5 rounded-full ring-1 ring-line"
                style={{ background: rampCss() }}
              />
              <div className="flex justify-between font-mono text-[9px] text-dim">
                <span>0 m</span>
                <span>{(depthScaleM / 2).toFixed(1)} m</span>
                <span>{depthScaleM.toFixed(1)} m</span>
              </div>
              <p className="text-[9px] text-dim">water depth (simulated)</p>
            </div>

            <SimulationStats />
          </>
        )}

        {fire && (
          <>
            <div className="space-y-1.5">
              <h3 className="font-mono text-[10px] tracking-[0.2em] text-dim uppercase">
                Layers
              </h3>
              <LayerToggle
                icon={Flame}
                label="Burned area"
                note="Modelled fire progression"
                on={showFlood}
                onClick={() => useSimulationStore.getState().setShowFlood(!showFlood)}
              />
              <LayerToggle
                icon={Mountain}
                label="Terrain relief"
                note="3D elevation under the burn"
                on={showTerrain}
                onClick={() => useSimulationStore.getState().setShowTerrain(!showTerrain)}
              />
            </div>

            <div className="rounded-xl bg-bg/70 ring-1 ring-line px-3 py-2.5 space-y-1">
              <span className="flex items-center gap-1.5 font-mono text-[9px] tracking-[0.18em] text-dim uppercase">
                <Wind size={10} /> Conditions
              </span>
              <p className="text-[11px] text-ink">
                {fire.meta.fuel_name}{" "}
                <span className="text-dim">({fire.meta.fuel_model})</span>
              </p>
              {fire.meta.wind_ms !== undefined && (
                <p className="text-[10px] text-dim">
                  {fire.meta.wind_ms} m/s midflame from{" "}
                  {compass(fire.meta.wind_from_bearing ?? 0)} ·{" "}
                  {(fire.durationMin / 60).toFixed(1)} h
                </p>
              )}
            </div>

            <Slider
              label="Front width"
              value={frontMinutes}
              min={2}
              max={60}
              step={1}
              suffix=" min"
              onChange={(v) => useSimulationStore.getState().setFrontMinutes(v)}
            />
            <Slider
              label="Opacity"
              value={opacity}
              min={0.1}
              max={1}
              step={0.05}
              suffix=""
              format={(v) => `${Math.round(v * 100)}%`}
              onChange={(v) => useSimulationStore.getState().setOpacity(v)}
            />

            {/* Burn-age legend — the same ramp the pixels use */}
            <div className="space-y-1">
              <div
                className="h-2.5 rounded-full ring-1 ring-line"
                style={{ background: burnRampCss() }}
              />
              <div className="flex justify-between font-mono text-[9px] text-dim">
                <span>burning now</span>
                <span>older burn</span>
              </div>
              <p className="text-[9px] text-dim">
                time since the front passed (simulated)
              </p>
            </div>

            <p className="text-[9px] text-dim leading-relaxed">
              Surface fire only — no crown fire, no spotting, no suppression.
              Fuel is uniform across the domain and the wind is steady.
            </p>
          </>
        )}
      </div>
    </motion.aside>
  );
}

function LayerToggle({
  icon: Icon,
  label,
  note,
  on,
  onClick,
}: {
  icon: typeof Waves;
  label: string;
  note: string;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2.5 rounded-xl ring-1 px-3 py-2.5 text-left transition ${
        on
          ? "bg-raised text-teal ring-teal/50"
          : "bg-bg/70 text-dim ring-line hover:text-ink"
      }`}
    >
      <Icon size={14} className={on ? "text-teal shrink-0" : "text-dim shrink-0"} />
      <span className="min-w-0">
        <span className="block text-xs text-ink">{label}</span>
        <span className="block text-[10px] text-dim leading-tight">{note}</span>
      </span>
      <span
        className={`ml-auto font-mono text-[9px] tracking-wider ${
          on ? "text-teal" : "text-dim"
        }`}
      >
        {on ? "ON" : "OFF"}
      </span>
    </button>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  suffix,
  format,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix: string;
  format?: (v: number) => string;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block space-y-1">
      <span className="flex items-center justify-between text-[11px]">
        <span className="text-dim">{label}</span>
        <span className="font-mono text-ink">
          {format ? format(value) : `${value.toFixed(2)}${suffix}`}
        </span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-teal h-1"
      />
    </label>
  );
}

/** The solver's own account of itself — mass closure included. */
function SimulationStats() {
  const sim = useSimulationStore((s) => s.sim);
  if (!sim) return null;
  const v = sim.meta.volume ?? {};
  const massError = typeof v.mass_error === "number" ? v.mass_error : null;

  return (
    <div className="rounded-xl bg-bg/70 ring-1 ring-line px-3 py-2.5 space-y-1.5">
      <span className="flex items-center gap-1.5 font-mono text-[9px] tracking-[0.18em] text-dim">
        <Layers3 size={10} />
        SOLVER
      </span>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px]">
        <Stat label="Peak depth" value={`${(sim.peakCm / 100).toFixed(2)} m`} />
        <Stat label="Grid" value={`${sim.nx}×${sim.ny}`} />
        <Stat label="Steps" value={(sim.meta.steps ?? 0).toLocaleString()} />
        <Stat label="Frames" value={String(sim.frames)} />
        {massError !== null && (
          <Stat
            label="Mass closure"
            value={massError === 0 ? "exact" : massError.toExponential(1)}
          />
        )}
        <Stat
          label="Resolution"
          value={sim.meta.decimated ? "decimated" : "native"}
        />
      </dl>
      {sim.meta.pits_filled && (
        <p className="text-[9px] text-dim leading-snug">
          DEM depressions were filled before solving — this changes the terrain
          and is reported because of it.
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-dim">{label}</dt>
      <dd className="font-mono text-ink text-right">{value}</dd>
    </>
  );
}
