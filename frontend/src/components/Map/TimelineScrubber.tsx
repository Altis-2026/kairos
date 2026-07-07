import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Pause, Play, X } from "lucide-react";
import { useMapStore } from "../../stores/mapStore";

export default function TimelineScrubber() {
  const timeline = useMapStore((s) => s.timeline);
  const index = useMapStore((s) => s.timelineIndex);
  const setIndex = useMapStore((s) => s.setTimelineIndex);
  const setLayerVisible = useMapStore((s) => s.setLayerVisible);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!timeline) return;
    timeline.frames.forEach((f, i) =>
      setLayerVisible(f.layerId, i === index)
    );
  }, [timeline, index, setLayerVisible]);

  useEffect(() => {
    if (!playing || !timeline) return;
    const id = setInterval(() => {
      const cur = useMapStore.getState().timelineIndex;
      const n = timeline.frames.length;
      useMapStore.getState().setTimelineIndex((cur + 1) % n);
    }, 1000);
    return () => clearInterval(id);
  }, [playing, timeline]);

  if (!timeline) return null;

  const frames = timeline.frames;
  const current = frames[index] ?? frames[0];

  function close() {
    setPlaying(false);
    const map = useMapStore.getState();
    map.clearGroup("timeline");
    map.setTimeline(null);
  }

  const values = frames.map((f) => f.value);
  const vmax = Math.max(...values, 1);
  const vmin = Math.min(...values, 0);
  const span = vmax - vmin || 1;
  const W = 100;
  const H = 28;
  const pts = frames.map((f, i) => {
    const x = frames.length === 1 ? 0 : (i / (frames.length - 1)) * W;
    const y = H - ((f.value - vmin) / span) * H;
    return [x, y] as const;
  });
  const path = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [cx, cy] = pts[index] ?? [0, 0];

  return (
    <motion.div
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      className="absolute top-20 left-1/2 -translate-x-1/2 z-30 w-[460px] max-w-[92vw] rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel px-4 py-3 pointer-events-auto"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
          TIME-SERIES · {timeline.metric.toUpperCase()}
        </span>
        <button onClick={close} className="text-dim hover:text-ink" title="Close time-series">
          <X size={14} />
        </button>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setPlaying((p) => !p)}
          className="h-9 w-9 shrink-0 grid place-items-center rounded-xl bg-amber text-bg hover:brightness-110 transition"
          title={playing ? "Pause" : "Play"}
        >
          {playing ? <Pause size={15} /> : <Play size={15} />}
        </button>

        <div className="flex-1">
          <input
            type="range"
            min={0}
            max={frames.length - 1}
            step={1}
            value={index}
            onChange={(e) => {
              setPlaying(false);
              setIndex(Number(e.target.value));
            }}
            className="w-full accent-teal h-1"
          />
          <div className="mt-1 flex items-center justify-between font-mono text-[10px] text-dim">
            <span>{frames[0].date}</span>
            <span>{frames[frames.length - 1].date}</span>
          </div>
        </div>

        <svg
          viewBox={`0 0 ${W} ${H}`}
          width={88}
          height={28}
          preserveAspectRatio="none"
          className="shrink-0"
        >
          <polyline
            points={path}
            fill="none"
            stroke="#00BFA8"
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
          />
          <circle cx={cx} cy={cy} r={2.5} fill="#E8A318" />
        </svg>
      </div>

      <div className="mt-2 flex items-baseline gap-2">
        <span className="font-display text-2xl text-teal">
          {current.value.toLocaleString()}
        </span>
        <span className="text-xs text-dim">{timeline.unit}</span>
        <span className="ml-auto font-mono text-[10px] text-dim">
          {current.date} · frame {index + 1}/{frames.length}
        </span>
      </div>
    </motion.div>
  );
}
