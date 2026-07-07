import { Square, Hexagon, MapPin } from "lucide-react";
import { useMapStore } from "../../../stores/mapStore";
import { useSidebarStore } from "../../../stores/sidebarStore";
import { aoiAreaKm2, aoiPerimeterKm } from "../../../lib/geo";

export default function DefineAOI() {
  const aoi = useMapStore((s) => s.aoi);
  const aoiPolygon = useMapStore((s) => s.aoiPolygon);
  const drawMode = useMapStore((s) => s.drawMode);
  const setDrawMode = useMapStore((s) => s.setDrawMode);
  const setAoi = useMapStore((s) => s.setAoi);
  const confirmAoi = useSidebarStore((s) => s.confirmAoi);
  const task = useSidebarStore((s) => s.selectedTask);

  const area = aoi ? aoiAreaKm2(aoi, aoiPolygon) : 0;
  const perimeter = aoi ? aoiPerimeterKm(aoi, aoiPolygon) : 0;
  const tooBig = aoi ? aoi[2] - aoi[0] > 10 || aoi[3] - aoi[1] > 10 : false;

  const toolButton = (
    mode: "rectangle" | "polygon" | "pin",
    icon: React.ReactNode,
    label: string
  ) => (
    <button
      onClick={() => setDrawMode(drawMode === mode ? null : mode)}
      className={`h-10 rounded-xl text-xs flex items-center justify-center gap-1.5 ring-1 transition-colors ${
        drawMode === mode
          ? "bg-raised text-amber ring-amber/50"
          : "text-dim ring-line hover:text-ink"
      }`}
    >
      {icon} {label}
    </button>
  );

  return (
    <div className="space-y-4">
      <p className="text-xs text-dim leading-relaxed">
        Where should{" "}
        <span className="text-ink">{task?.display_name ?? "the analysis"}</span>{" "}
        run? Draw directly on the globe.
      </p>

      <div className="grid grid-cols-3 gap-2">
        {toolButton("rectangle", <Square size={14} />, "Rectangle")}
        {toolButton("polygon", <Hexagon size={14} />, "Polygon")}
        {toolButton("pin", <MapPin size={14} />, "Pin")}
      </div>

      {drawMode === "rectangle" && (
        <p className="font-mono text-[10px] text-amber/90">
          Click and drag on the globe to draw the box.
        </p>
      )}
      {drawMode === "polygon" && (
        <p className="font-mono text-[10px] text-amber/90">
          Click the globe to add points. Double-click, press Enter, or click
          the first point again to close the shape. Esc cancels.
        </p>
      )}
      {drawMode === "pin" && (
        <p className="font-mono text-[10px] text-amber/90">
          Click the globe. A box roughly 50 km across is created around the pin.
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
          <div className="flex justify-between text-xs">
            <span className="text-dim">Perimeter</span>
            <span className="font-mono text-teal">
              {perimeter.toLocaleString()} km
            </span>
          </div>
          {aoiPolygon && (
            <div className="flex justify-between text-xs">
              <span className="text-dim">Shape</span>
              <span className="font-mono text-teal">
                free-hand, {aoiPolygon.length} points
              </span>
            </div>
          )}
          <div className="font-mono text-[10px] text-dim leading-relaxed break-all">
            [{aoi.map((v) => v.toFixed(3)).join(", ")}]
          </div>
          {tooBig && (
            <p className="text-[11px] text-amber leading-relaxed">
              This area is larger than 10° across. Analyses may time out, so
              consider a smaller shape.
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
