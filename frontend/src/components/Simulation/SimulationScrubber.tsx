import { useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { Box, Flame, Gauge, Pause, Play, SkipBack, SkipForward, Waves, X } from "lucide-react";
import { useSimulationStore } from "../../stores/simulationStore";
import { burnColour, burnedHectares, frontFlameLength } from "../../lib/fire";
import { depthColor, formatElapsed, frameAreaKm2, framePeakM } from "../../lib/simulation";

const FRAME_MS = 220;

export default function SimulationScrubber() {
  const sim = useSimulationStore((s) => s.sim);
  const fire = useSimulationStore((s) => s.fire);
  const frontMinutes = useSimulationStore((s) => s.frontMinutes);
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

  const peaks = useMemo(() => {
    if (!sim) return [] as number[];
    return Array.from({ length: sim.frames }, (_, i) => framePeakM(sim, i));
  }, [sim]);

  const areas = useMemo(() => {
    if (!sim) return [] as number[];
    return Array.from({ length: sim.frames }, (_, i) => frameAreaKm2(sim, i));
  }, [sim]);

  const fireSeries = useMemo(() => {
    if (!fire) return { area: [] as number[], flame: [] as number[] };
    return {
      area: fire.times.map((t) => burnedHectares(fire, t)),
      flame: fire.times.map((t) => frontFlameLength(fire, t, frontMinutes)),
    };
  }, [fire, frontMinutes]);

  useEffect(() => {
    if (!playing || (!sim && !fire)) return;
    const id = setInterval(() => {
      const s = useSimulationStore.getState();
      const frames = s.sim?.frames ?? s.fire?.frames;
      if (!frames) return;

      s.setFrame((s.frame + 1) % frames);
    }, FRAME_MS / speed);
    return () => clearInterval(id);
  }, [playing, speed, sim, fire]);

  if (!sim && !fire) return null;

  const isFire = !!fire;
  const solve = (sim ?? fire)!;

  const track = isFire
    ? {
        title: fire!.meta.scene_name ?? "Wildfire simulation",
        grid: `${fire!.nx}×${fire!.ny} @ ${fire!.meta.dx.toFixed(0)}m`,
        series: fireSeries.area,

        elapsedSeconds: (fire!.times[frame] ?? 0) * 60,
        totalSeconds: (fire!.durationMin ?? 0) * 60,
        headline: {
          value: (fireSeries.flame[frame] ?? 0).toFixed(1),
          unit: "m flame length",
          colour: (() => {
            const c = burnColour(0, frontMinutes)!;
            return `rgb(${c[0]},${c[1]},${c[2]})`;
          })(),
        },
        secondary: {
          value: (fireSeries.area[frame] ?? 0).toLocaleString(undefined, {
            maximumFractionDigits: 0,
          }),
          unit: "ha burned",
        },
        sparkStroke: "#F4743B",
      }
    : {
        title: sim!.meta.scene_name ?? "Flood simulation",
        grid: `${sim!.nx}×${sim!.ny} @ ${sim!.meta.dx.toFixed(0)}m`,
        series: peaks,
        elapsedSeconds: sim!.times[frame] ?? 0,
        totalSeconds: sim!.times[sim!.times.length - 1] ?? 0,
        headline: {
          value: (peaks[frame] ?? 0).toFixed(2),
          unit: "m peak depth",
          colour: depthColor(peaks[frame] ?? 0, Math.max(...peaks, 0.001)),
        },
        secondary: {
          value: (areas[frame] ?? 0).toFixed(2),
          unit: "km² flooded",
        },
        sparkStroke: "#3BA7FF",
      };

  const seriesMax = Math.max(...track.series, 0.001);
  const progress = solve.frames > 1 ? frame / (solve.frames - 1) : 0;

  const W = 100;
  const H = 22;
  const points = track.series
    .map((p, i) => {
      const x = track.series.length === 1 ? 0 : (i / (track.series.length - 1)) * W;

      const y = H - (p / seriesMax) * H;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, x: "-50%" }}
      animate={{ opacity: 1, y: 0, x: "-50%" }}
      exit={{ opacity: 0, y: 16, x: "-50%" }}
      transition={{ type: "spring", stiffness: 320, damping: 32 }}
      className="absolute bottom-24 left-1/2 z-50 w-[640px] max-w-[94vw] rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel px-4 py-3 pointer-events-auto"
    >
      <div className="flex items-center gap-2.5 mb-3">
        <span className="inline-flex items-center gap-1.5 rounded-md bg-amber/15 ring-1 ring-amber/40 px-2 py-[3px] font-mono text-[9px] tracking-[0.18em] text-amber shrink-0">
          {isFire ? <Flame size={10} /> : <Waves size={10} />}
          SIMULATED
        </span>
        <span className="text-xs text-ink truncate min-w-0">{track.title}</span>
        <span className="font-mono text-[10px] text-dim shrink-0 hidden sm:inline">{track.grid}</span>
        <button
          onClick={() => setView3d(!view3d)}
          className={`ml-auto shrink-0 h-6 px-2 rounded-md ring-1 font-mono text-[9px] tracking-wider transition ${
            view3d ? "bg-teal text-bg ring-teal" : "text-dim ring-line hover:text-ink hover:ring-teal/50"
          }`}
          aria-label={view3d ? "Back to the globe" : "Open the 3D terrain view"}
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
          aria-label="Close simulation"
          title="Close simulation"
        >
          <X size={15} />
        </button>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => {
              setPlaying(false);
              stepFrame(-1);
            }}
            className="h-7 w-7 grid place-items-center rounded-lg text-dim hover:text-ink transition-colors"
            aria-label="Previous frame"
            title="Previous frame"
          >
            <SkipBack size={13} />
          </button>
          <button
            onClick={togglePlaying}
            className="h-10 w-10 grid place-items-center rounded-xl bg-teal text-bg hover:brightness-110 transition shadow-glow"
            aria-label={playing ? "Pause" : "Play"}
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
            aria-label="Next frame"
            title="Next frame"
          >
            <SkipForward size={13} />
          </button>
        </div>

        <div className="flex-1 min-w-0">
          <div className="relative h-6 flex items-center">
            <div className="absolute inset-x-0 h-[5px] rounded-full bg-bg ring-1 ring-line overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-teal/70 to-teal transition-[width] duration-100"
                style={{ width: `${progress * 100}%` }}
              />
            </div>

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
              max={solve.frames - 1}
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
            <span>{formatElapsed(track.elapsedSeconds)}</span>
            <span>
              frame {frame + 1}/{solve.frames}
            </span>
            <span>{formatElapsed(track.totalSeconds)}</span>
          </div>
        </div>

        <button
          onClick={cycleSpeed}
          className="shrink-0 h-8 px-2.5 rounded-lg bg-bg/70 ring-1 ring-line font-mono text-[11px] text-ink hover:ring-teal/50 transition"
          aria-label="Playback speed"
          title="Playback speed"
        >
          {speed}×
        </button>

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
            stroke={track.sparkStroke}
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
          />
          <circle
            cx={track.series.length === 1 ? 0 : (frame / (track.series.length - 1)) * W}
            cy={H - ((track.series[frame] ?? 0) / seriesMax) * H}
            r={2.5}
            fill="#E8A318"
          />
        </svg>
      </div>

      <div className="mt-2.5 flex items-baseline gap-4 flex-wrap">
        <span className="flex items-baseline gap-1.5">
          <span className="font-display text-2xl leading-none" style={{ color: track.headline.colour }}>
            {track.headline.value}
          </span>
          <span className="text-[11px] text-dim">{track.headline.unit}</span>
        </span>
        <span className="flex items-baseline gap-1.5">
          <span className="font-display text-lg leading-none text-ink">{track.secondary.value}</span>
          <span className="text-[11px] text-dim">{track.secondary.unit}</span>
        </span>
        <span className="ml-auto flex items-center gap-1.5 font-mono text-[9px] text-dim">
          <Gauge size={11} />
          modelled, not observed
        </span>
      </div>
    </motion.div>
  );
}
