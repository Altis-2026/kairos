import { useEffect, useState } from "react";
import { API_BASE } from "../api/client";
import { useMapStore } from "../stores/mapStore";

export default function TelemetryFooter() {
  const coords = useMapStore((s) => s.coords);
  const [apiUp, setApiUp] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = () =>
      fetch(`${API_BASE}/health`)
        .then((r) => !cancelled && setApiUp(r.ok))
        .catch(() => !cancelled && setApiUp(false));
    check();
    const t = setInterval(check, 30000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  const fmt = (v: number, pos: string, neg: string) =>
    `${Math.abs(v).toFixed(4)}°${v >= 0 ? pos : neg}`;

  return (
    <div className="absolute left-5 bottom-5 z-20 hidden sm:flex items-center gap-3 font-mono text-[10px] text-dim pointer-events-none select-none">
      <span className="flex items-center gap-1.5 bg-surface/80 backdrop-blur rounded-full px-3 py-1.5 ring-1 ring-line pointer-events-auto">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            apiUp === null
              ? "bg-dim"
              : apiUp
              ? "bg-teal animate-pulse-soft"
              : "bg-amber"
          }`}
        />
        {apiUp === null ? "LINKING…" : apiUp ? "KAIROS LINK ACTIVE" : "API OFFLINE"}
      </span>
      {coords && (
        <span className="bg-surface/80 backdrop-blur rounded-full px-3 py-1.5 ring-1 ring-line tracking-wider">
          {fmt(coords.lat, "N", "S")} · {fmt(coords.lng, "E", "W")}
        </span>
      )}
    </div>
  );
}
