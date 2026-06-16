/** Step 2 — define the area of interest on the globe. */
import { Square, MapPin } from "lucide-react";
import { useMapStore } from "../../../stores/mapStore";
import { useSidebarStore } from "../../../stores/sidebarStore";

function approxAreaKm2(bbox: [number, number, number, number]): number {
  const [minLon, minLat, maxLon, maxLat] = bbox;
  const midLat = ((minLat + maxLat) / 2) * (Math.PI / 180);
  const wKm = (maxLon - minLon) * 111.32 * Math.cos(midLat);
  const hKm = (maxLat - minLat) * 110.57;
  return Math.round(Math.abs(wKm * hKm));
}

export default function DefineAOI() {
  const aoi = useMapStore((s) => s.aoi);
  const drawMode = useMapStore((s) => s.drawMode);
  const setDrawMode = useMapStore((s) => s.setDrawMode);
  const setAoi = useMapStore((s) => s.setAoi);
  const confirmAoi = useSidebarStore((s) => s.confirmAoi);
  const task = useSidebarStore((s) => s.selectedTask);

  const area = aoi ? approxAreaKm2(aoi) : 0;
  const tooBig = aoi ? aoi[2] - aoi[0] > 10 || aoi[3] - aoi[1] > 10 : false;

  return (
    <div className="space-y-4">
      <p className="text-xs text-dim leading-relaxed">
        Where should{" "}
        <span className="text-ink">{task?.display_name ?? "the analysis"}</span>{" "}
        run? Draw directly on the globe.
      </p>

      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={() => setDrawMode(drawMode === "rectangle" ? null : "rectangle")}
          className={`h-10 rounded-xl text-xs flex items-center justify-center gap-2 ring-1 transition-colors ${
            drawMode === "rectangle"
              ? "bg-raised text-amber ring-amber/50"
              : "text-dim ring-line hover:text-ink"
          }`}
        >
          <Square size={14} /> Draw rectangle
        </button>
        <button
          onClick={() => setDrawMode(drawMode === "pin" ? null : "pin")}
          className={`h-10 rounded-xl text-xs flex items-center justify-center gap-2 ring-1 transition-colors ${
            drawMode === "pin"
              ? "bg-raised text-amber ring-amber/50"
              : "text-dim ring-line hover:text-ink"
          }`}
        >
          <MapPin size={14} /> Drop pin
        </button>
      </div>

      {drawMode === "rectangle" && (
        <p className="font-mono text-[10px] text-amber/90">
          Click and drag on the globe to draw the box.
        </p>
      )}
      {drawMode === "pin" && (
        <p className="font-mono text-[10px] text-amber/90">
          Click the globe — a ~50 km box is created around the pin.
        </p>
      )}

      {aoi ? (
        <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3 space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-dim">Area</span>
            <span className="font-mono text-teal">
              {area.toLocaleString()} km²
            </span>
          </div>
          <div className="font-mono text-[10px] text-dim leading-relaxed break-all">
            [{aoi.map((v) => v.toFixed(3)).join(", ")}]
          </div>
          {tooBig && (
            <p className="text-[11px] text-amber leading-relaxed">
              This area is larger than 10° across — analyses may time out.
              Consider a smaller box.
            </p>
          )}
          <button
            onClick={() => setAoi(null)}
            className="text-[11px] text-dim hover:text-ink underline underline-offset-2"
          >
            Clear and redraw
          </button>
        </div>
      ) : (
        <div className="rounded-xl bg-bg/70 ring-1 ring-line p-3 text-xs text-dim">
          No area selected yet.
        </div>
      )}

      <button
        disabled={!aoi}
        onClick={confirmAoi}
        className="w-full h-10 rounded-xl bg-amber text-bg text-sm font-medium hover:brightness-110 transition disabled:opacity-40"
      >
        Use this area
      </button>
    </div>
  );
}
