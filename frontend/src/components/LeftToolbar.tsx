import { MousePointer2, Square, Hexagon, MapPin, Zap, Eraser } from "lucide-react";
import { useMapStore } from "../stores/mapStore";
import { aoiAreaKm2, aoiPerimeterKm } from "../lib/geo";

export default function LeftToolbar() {
  const drawMode = useMapStore((s) => s.drawMode);
  const setDrawMode = useMapStore((s) => s.setDrawMode);
  const setAoi = useMapStore((s) => s.setAoi);
  const aoi = useMapStore((s) => s.aoi);
  const aoiPolygon = useMapStore((s) => s.aoiPolygon);

  const Item = ({
    title,
    active,
    onClick,
    children,
  }: {
    title: string;
    active?: boolean;
    onClick: () => void;
    children: React.ReactNode;
  }) => (
    <button
      title={title}
      aria-label={title}
      onClick={onClick}
      className={`h-10 w-10 grid place-items-center transition-colors ${
        active ? "text-amber" : "text-dim hover:text-ink"
      }`}
    >
      {children}
    </button>
  );

  return (
    <>
      <div className="absolute left-2 sm:left-5 top-1/2 -translate-y-1/2 z-30 flex flex-col items-center rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel divide-y divide-line">
        <Item
          title="Select / pan"
          active={drawMode === null}
          onClick={() => setDrawMode(null)}
        >
          <MousePointer2 size={17} />
        </Item>
        <Item
          title="Draw rectangle AOI (click and drag)"
          active={drawMode === "rectangle"}
          onClick={() => setDrawMode(drawMode === "rectangle" ? null : "rectangle")}
        >
          <Square size={17} />
        </Item>
        <Item
          title="Draw polygon AOI (click to add points, double-click to close)"
          active={drawMode === "polygon"}
          onClick={() => setDrawMode(drawMode === "polygon" ? null : "polygon")}
        >
          <Hexagon size={17} />
        </Item>
        <Item
          title="Drop a pin (creates a ~50 km box)"
          active={drawMode === "pin"}
          onClick={() => setDrawMode(drawMode === "pin" ? null : "pin")}
        >
          <MapPin size={17} />
        </Item>
        <Item
          title="Quick analysis: drop a pin and run instantly"
          active={drawMode === "quickpin"}
          onClick={() => setDrawMode(drawMode === "quickpin" ? null : "quickpin")}
        >
          <Zap size={17} />
        </Item>
        {aoi && (
          <Item title="Clear area of interest" onClick={() => setAoi(null)}>
            <Eraser size={17} />
          </Item>
        )}
      </div>

      {aoi && (
        <div className="absolute left-14 sm:left-[70px] top-1/2 -translate-y-1/2 z-20 rounded-xl bg-surface/90 backdrop-blur ring-1 ring-line px-3 py-2 font-mono text-[10px] pointer-events-none select-none">
          <div className="text-teal">
            {aoiAreaKm2(aoi, aoiPolygon).toLocaleString()} km²
          </div>
          <div className="text-dim">
            {aoiPerimeterKm(aoi, aoiPolygon).toLocaleString()} km edge
          </div>
          {aoiPolygon && (
            <div className="text-dim">{aoiPolygon.length} vertices</div>
          )}
        </div>
      )}

      {drawMode === "polygon" && (
        <div className="absolute left-1/2 -translate-x-1/2 top-20 z-30 rounded-full bg-surface/95 backdrop-blur ring-1 ring-amber/40 px-4 py-2 font-mono text-[10px] text-amber pointer-events-none select-none">
          Click to add points. Double-click, press Enter, or click the first point to close. Esc cancels.
        </div>
      )}
    </>
  );
}
