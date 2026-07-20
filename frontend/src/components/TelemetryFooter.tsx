/**
 * Bottom-left telemetry readout — the radar signature motif.
 * Live cursor coordinates in mono + API connection status.
 */
import { useEffect, useState } from "react";
import { API_BASE } from "../api/client";
import { useMapStore } from "../stores/mapStore";

// Steady-state poll once healthy. Before that, retry fast (2s/4s/8s/16s) so
// a Cloud Run cold start resolves within seconds instead of sitting on a
// stale status for up to a full 30s poll cycle. keep-warm.yml pings /health
// every 10 minutes in production, so the backend should rarely be cold.
const STEADY_INTERVAL_MS = 30000;
const RETRY_MS = [2000, 4000, 8000, 16000];

export default function TelemetryFooter() {
  const coords = useMapStore((s) => s.coords);
  const [apiUp, setApiUp] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    let everUp = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout>;

    const scheduleNext = () => {
      if (cancelled) return;
      const delay = everUp
        ? STEADY_INTERVAL_MS
        : RETRY_MS[Math.min(attempt, RETRY_MS.length - 1)];
      timer = setTimeout(check, delay);
    };

    const check = () => {
      fetch(`${API_BASE}/health`)
        .then((r) => {
          if (cancelled) return;
          setApiUp(r.ok);
          if (r.ok) everUp = true;
          else attempt++;
          scheduleNext();
        })
        .catch(() => {
          if (cancelled) return;
          setApiUp(false);
          attempt++;
          scheduleNext();
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
    <div className="absolute left-5 bottom-5 z-20 flex items-center gap-3 font-mono text-[10px] text-dim pointer-events-none select-none">
      <span className="flex items-center gap-1.5 bg-surface/80 backdrop-blur rounded-full px-3 py-1.5 ring-1 ring-line pointer-events-auto">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            apiUp === null
              ? "bg-amber animate-pulse-soft"
              : apiUp
              ? "bg-teal animate-pulse-soft"
              : "bg-amber"
          }`}
        />
        {apiUp === null
          ? "LINKING…"
          : apiUp
          ? "KAIROS LINK ACTIVE"
          : "API OFFLINE"}
      </span>
      {coords && (
        <span className="bg-surface/80 backdrop-blur rounded-full px-3 py-1.5 ring-1 ring-line tracking-wider">
          {fmt(coords.lat, "N", "S")} · {fmt(coords.lng, "E", "W")}
        </span>
      )}
    </div>
  );
}
