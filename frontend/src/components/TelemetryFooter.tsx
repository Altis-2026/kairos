import { useEffect, useState } from "react";
import { API_BASE } from "../api/client";
import { useMapStore } from "../stores/mapStore";

const STEADY_INTERVAL_MS = 30000;
const RETRY_MS = [2000, 4000, 8000, 16000];
const FAILS_BEFORE_OFFLINE = 3;

export default function TelemetryFooter() {
  const coords = useMapStore((s) => s.coords);
  const [state, setState] = useState<"linking" | "up" | "waking" | "down">(
    "linking"
  );

  useEffect(() => {
    let cancelled = false;
    let everUp = false;
    let fails = 0;
    let timer: ReturnType<typeof setTimeout>;

    const scheduleNext = () => {
      if (cancelled) return;
      const delay =
        fails === 0
          ? STEADY_INTERVAL_MS
          : RETRY_MS[Math.min(fails - 1, RETRY_MS.length - 1)];
      timer = setTimeout(check, delay);
    };

    const onFail = () => {
      fails++;
      setState(fails >= FAILS_BEFORE_OFFLINE ? "down" : everUp ? "waking" : "linking");
      scheduleNext();
    };

    const check = () => {
      fetch(`${API_BASE}/health`)
        .then((r) => {
          if (cancelled) return;
          if (r.ok) {
            everUp = true;
            fails = 0;
            setState("up");
            scheduleNext();
          } else {
            onFail();
          }
        })
        .catch(() => {
          if (!cancelled) onFail();
        });
    };

    check();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  const fmt = (v: number, pos: string, neg: string) =>
    `${Math.abs(v).toFixed(4)}°${v >= 0 ? pos : neg}`;

  return (
    <div className="absolute left-5 bottom-5 z-20 hidden sm:flex items-center gap-3 font-mono text-[10px] text-dim pointer-events-none select-none">
      <span className="flex items-center gap-1.5 bg-surface/80 backdrop-blur rounded-full px-3 py-1.5 ring-1 ring-line pointer-events-auto">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            state === "up"
              ? "bg-teal animate-pulse-soft"
              : state === "down"
              ? "bg-amber"
              : "bg-amber animate-pulse-soft"
          }`}
        />
        {state === "up"
          ? "KAIROS LINK ACTIVE"
          : state === "down"
          ? "RECONNECTING…"
          : state === "waking"
          ? "WAKING LINK…"
          : "LINKING…"}
      </span>
      {coords && (
        <span className="bg-surface/80 backdrop-blur rounded-full px-3 py-1.5 ring-1 ring-line tracking-wider">
          {fmt(coords.lat, "N", "S")} · {fmt(coords.lng, "E", "W")}
        </span>
      )}
    </div>
  );
}
