/** Left tool palette: select / draw rectangle AOI / drop pin / quick analysis / clear. */
import { MousePointer2, Square, MapPin, Zap, Eraser } from "lucide-react";
import { useMapStore } from "../stores/mapStore";

export default function LeftToolbar() {
  const drawMode = useMapStore((s) => s.drawMode);
  const setDrawMode = useMapStore((s) => s.setDrawMode);
  const setAoi = useMapStore((s) => s.setAoi);
  const aoi = useMapStore((s) => s.aoi);

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
      onClick={onClick}
      className={`h-10 w-10 grid place-items-center transition-colors ${
        active ? "text-amber" : "text-dim hover:text-ink"
      }`}
    >
      {children}
    </button>
  );

  return (
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
        title="Drop a pin (creates a ~50 km box)"
        active={drawMode === "pin"}
        onClick={() => setDrawMode(drawMode === "pin" ? null : "pin")}
      >
        <MapPin size={17} />
      </Item>
      <Item
        title="Quick analysis — drop a pin and run instantly"
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
  );
}
