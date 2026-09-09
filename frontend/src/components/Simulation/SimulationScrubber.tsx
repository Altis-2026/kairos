/**
 * Playback control for a flood simulation.
 *
 * Floats above the chat bar and owns the time axis: play/pause, speed, a
 * scrubbable track, and the live readouts for the frame on screen.
 *
 * The SIMULATED badge is not decoration. This panel is the one piece of UI
 * that is always on screen while modelled water is being displayed, so it is
 * where the observed/simulated distinction has to be impossible to miss —
 * hence the amber pill, the explicit wording, and the disclosure line rather
 * than a subtle colour cue someone could read past.
 */
import { useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { Box, Gauge, Pause, Play, SkipBack, SkipForward, Waves, X } from "lucide-react";
import { useSimulationStore } from "../../stores/simulationStore";
import {
  depthColor,
  formatElapsed,
  frameAreaKm2,
  framePeakM,
} from "../../lib/simulation";

/** Wall-clock milliseconds per frame at 1x. */
const FRAME_MS = 220;

export default function SimulationScrubber() {
  const sim = useSimulationStore((s) => s.sim);
  const frame = useSimulationStore((s) => s.frame);
  const playing = useSimulationStore((s) => s.playing);
  const speed = useSimulationStore((s) => s.speed);
  const setFrame = useSimulationStore((s) => s.setFrame);
  const stepFrame = useSimulationStore((s) => s.stepFrame);
  const togglePlaying = useSimulationStore((s) => s.togglePlaying);
  const setPlaying = useSimulationStore((s) => s.setPlaying);
  const cycleSpeed = useSimulationStore((s) => s.cycleSpeed);
  const clearSimulation = useSimulationStore((s) => s.clearSimulation);
  const view3d = useSimulationStore((s) => s.view3d);
  const setView3d = useSimulationStore((s) => s.setView3d);

  // Per-frame peak depth, for the sparkline and the readout. Computed once
  // per simulation — it is a full pass over every cell of every frame.
  const peaks = useMemo(() => {
    if (!sim) return [] as number[];
    return Array.from({ length: sim.frames }, (_, i) => framePeakM(sim, i));
  }, [sim]);

  const areas = useMemo(() => {
    if (!sim) return [] as number[];
    return Array.from({ length: sim.frames }, (_, i) => frameAreaKm2(sim, i));
  }, [sim]);

  // Playback loop.
  useEffect(() => {
    if (!playing || !sim) return;
    const id = setInterval(() => {
      const s = useSimulationStore.getState();
      if (!s.sim) return;
      // Loop rather than stop: a flood that rises and drains reads best on
      // repeat, and stopping dead on the last frame hides the recession.
      s.setFrame((s.frame + 1) % s.sim.frames);
    }, FRAME_MS / speed);
    return () => clearInterval(id);
  }, [playing, speed, sim]);

  if (!sim) return null;

  const peakNow = peaks[frame] ?? 0;
  const areaNow = areas[frame] ?? 0;
  const scenePeak = Math.max(...peaks, 0.001);
  const progress = sim.frames > 1 ? frame / (sim.frames - 1) : 0;
  const elapsed = sim.times[frame] ?? 0;

  // Sparkline geometry over the peak-depth series.
  const W = 100;
  const H = 22;
  const points = peaks
    .map((p, i) => {
      const x = peaks.length === 1 ? 0 : (i / (peaks.length - 1)) * W;
      const y = H - (p / scenePeak) * H;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <motion.div
      // The horizontal centring lives in the animation, not in a
      // `-translate-x-1/2` class: framer-motion writes its own inline
      // `transform` for the y animation, which silently overrides the
      // Tailwind translate and leaves the panel half a width to the right —
      // far enough to sit under the tools panel.
      initial={{ opacity: 0, y: 16, x: "-50%" }}
      animate={{ opacity: 1, y: 0, x: "-50%" }}
      exit={{ opacity: 0, y: 16, x: "-50%" }}
      transition={{ type: "spring", stiffness: 320, damping: 32 }}
      className="absolute bottom-24 left-1/2 z-50 w-[640px] max-w-[94vw] rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel px-4 py-3 pointer-events-auto"
    >
      {/* Header — badge, scene, close */}
      <div className="flex items-center gap-2.5 mb-3">
        <span className="inline-flex items-center gap-1.5 rounded-md bg-amber/15 ring-1 ring-amber/40 px-2 py-[3px] font-mono text-[9px] tracking-[0.18em] text-amber shrink-0">
          <Waves size={10} />
          SIMULATED
        </span>
        <span className="text-xs text-ink truncate min-w-0">
          {sim.meta.scene_name ?? "Flood simulation"}
        </span>
        <span className="font-mono text-[10px] text-dim shrink-0 hidden sm:inline">
          {sim.nx}×{sim.ny} @ {sim.meta.dx.toFixed(0)}m
        </span>
        <button
          onClick={() => setView3d(!view3d)}
          className={`ml-auto shrink-0 h-6 px-2 rounded-md ring-1 font-mono text-[9px] tracking-wider transition ${
            view3d
              ? "bg-teal text-bg ring-teal"
              : "text-dim ring-line hover:text-ink hover:ring-teal/50"
          }`}
          title={view3d ? "Back to the globe" : "Open the 3D terrain view"}
        >
          <span className="inline-flex items-center gap-1">
            <Box size={10} />
            3D
          </span>
        </button>
        <button
          onClick={clearSimulation}
          className="text-dim hover:text-ink transition-colors shrink-0"
          title="Close simulation"
        >
          <X size={15} />
        </button>
      </div>

      <div className="flex items-center gap-3">
        {/* Transport controls */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => {
              setPlaying(false);
              stepFrame(-1);
            }}
            className="h-7 w-7 grid place-items-center rounded-lg text-dim hover:text-ink transition-colors"
            title="Previous frame"
          >
            <SkipBack size={13} />
          </button>
          <button
            onClick={togglePlaying}
            className="h-10 w-10 grid place-items-center rounded-xl bg-teal text-bg hover:brightness-110 transition shadow-glow"
            title={playing ? "Pause" : "Play"}
          >
            {playing ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
          </button>
          <button
            onClick={() => {
              setPlaying(false);
              stepFrame(1);
            }}
            className="h-7 w-7 grid place-items-center rounded-lg text-dim hover:text-ink transition-colors"
            title="Next frame"
          >
            <SkipForward size={13} />
          </button>
        </div>

        {/* Track — styled rail with an invisible range input over it, so it
            looks designed but still drags and takes arrow keys natively. */}
        <div className="flex-1 min-w-0">
          <div className="relative h-6 flex items-center">
            <div className="absolute inset-x-0 h-[5px] rounded-full bg-bg ring-1 ring-line overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-teal/70 to-teal transition-[width] duration-100"
                style={{ width: `${progress * 100}%` }}
              />
            </div>
            {/* Frame ticks */}
            <div className="absolute inset-x-0 flex justify-between pointer-events-none px-[1px]">
              {peaks.map((_, i) =>
                i % 6 === 0 ? (
                  <span key={i} className="h-[9px] w-px bg-line" />
                ) : (
                  <span key={i} className="h-0 w-px" />
                )
              )}
            </div>
            <div
              className="absolute h-3.5 w-3.5 rounded-full bg-ink ring-2 ring-teal shadow pointer-events-none transition-[left] duration-100"
              style={{ left: `calc(${progress * 100}% - 7px)` }}
            />
            <input
              type="range"
              min={0}
              max={sim.frames - 1}
              step={1}
              value={frame}
              onChange={(e) => {
                setPlaying(false);
                setFrame(Number(e.target.value));
              }}
              className="absolute inset-x-0 w-full h-6 opacity-0 cursor-pointer"
              aria-label="Simulation time"
            />
          </div>
          <div className="flex items-center justify-between font-mono text-[10px] text-dim">
            <span>{formatElapsed(elapsed)}</span>
            <span>
              frame {frame + 1}/{sim.frames}
            </span>
            <span>{formatElapsed(sim.times[sim.times.length - 1] ?? 0)}</span>
          </div>
        </div>

        {/* Speed */}
        <button
          onClick={cycleSpeed}
          className="shrink-0 h-8 px-2.5 rounded-lg bg-bg/70 ring-1 ring-line font-mono text-[11px] text-ink hover:ring-teal/50 transition"
          title="Playback speed"
        >
          {speed}×
        </button>

        {/* Sparkline of peak depth over the event */}
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width={84}
          height={26}
          preserveAspectRatio="none"
          className="shrink-0 hidden md:block"
          aria-hidden
        >
          <polyline
            points={points}
            fill="none"
            stroke="#3BA7FF"
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
          />
          <circle
            cx={peaks.length === 1 ? 0 : (frame / (peaks.length - 1)) * W}
            cy={H - (peakNow / scenePeak) * H}
            r={2.5}
            fill="#E8A318"
          />
        </svg>
      </div>

      {/* Live readouts for the frame on screen */}
      <div className="mt-2.5 flex items-baseline gap-4 flex-wrap">
        <span className="flex items-baseline gap-1.5">
          <span
            className="font-display text-2xl leading-none"
            style={{ color: depthColor(peakNow, scenePeak) }}
          >
            {peakNow.toFixed(2)}
          </span>
          <span className="text-[11px] text-dim">m peak depth</span>
        </span>
        <span className="flex items-baseline gap-1.5">
          <span className="font-display text-lg leading-none text-ink">
            {areaNow.toFixed(2)}
          </span>
          <span className="text-[11px] text-dim">km² flooded</span>
        </span>
        <span className="ml-auto flex items-center gap-1.5 font-mono text-[9px] text-dim">
          <Gauge size={11} />
          modelled, not observed
        </span>
      </div>
    </motion.div>
  );
}
