/**
 * Bottom-left telemetry readout — the radar signature motif.
 * Live cursor coordinates in mono + API connection status.
 */
import { useEffect, useState } from "react";
import { API_BASE } from "../api/client";
import { useMapStore } from "../stores/mapStore";

// Steady-state poll once healthy. Before that, retry fast (2s/4s/8s/16s) so
// a Cloud Run cold start — the backend waking up, not actually broken —
// resolves within seconds instead of sitting on a scary "OFFLINE" state for
// up to a full 30s poll cycle. But "waking up" is an optimistic guess, not a
// promise: if it's still failing after this many fast retries (~30s), it
// stops guessing and calls it what it is — actually offline — instead of
// saying "WAKING UP" forever.
const STEADY_INTERVAL_MS = 30000;
const COLD_START_RETRY_MS = [2000, 4000, 8000, 16000];
const MAX_WAKING_ATTEMPTS = 6;

export default function TelemetryFooter() {
  const coords = useMapStore((s) => s.coords);
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let everUp = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout>;

    const scheduleNext = () => {
      if (cancelled) return;
      const delay = everUp
        ? STEADY_INTERVAL_MS
        : COLD_START_RETRY_MS[Math.min(attempt, COLD_START_RETRY_MS.length - 1)];
      timer = setTimeout(check, delay);
    };

    const check = () => {
      fetch(`${API_BASE}/health`)
        .then((r) => {
          if (cancelled) return;
          setApiUp(r.ok);
          setWaking(false);
          if (r.ok) everUp = true;
          else attempt++;
          scheduleNext();
        })
        .catch(() => {
          if (cancelled) return;
          setApiUp(false);
          // "Still waking up" only before we've ever seen it up, and only for
          // a bounded number of attempts. A backend that goes down AFTER
          // working is a real outage, not a cold start, and reads as OFFLINE
          // immediately; one that never comes up after ~30s of fast retries
          // stops getting the benefit of the doubt too — it's actually down.
          setWaking(!everUp && attempt < MAX_WAKING_ATTEMPTS);
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
            apiUp === null || waking
              ? "bg-amber animate-pulse-soft"
              : apiUp
              ? "bg-teal animate-pulse-soft"
              : "bg-amber"
          }`}
        />
        {apiUp === null
          ? "LINKING…"
          : waking
          ? "WAKING UP…"
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
