import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import {
  BookOpen,
  Eraser,
  MapPin,
  MousePointer2,
  Pentagon,
  Square,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { useMapStore } from "../stores/mapStore";
import { aoiAreaKm2 } from "../lib/geo";
import { playStory } from "../lib/featured";
import StoriesMenu from "./Map/StoriesMenu";
import type { DrawMode } from "../types/map";

interface Tool {
  label: string;
  icon: LucideIcon;
  mode?: DrawMode;
  tour?: string;
}

const TOOLS: Tool[] = [
  { label: "Select and pan", icon: MousePointer2, mode: null },
  { label: "Draw a rectangle (click and drag)", icon: Square, mode: "rectangle", tour: "draw" },
  { label: "Trace a shape (click points, double-click to finish)", icon: Pentagon, mode: "polygon" },
  { label: "Drop a pin (makes a 50 km box)", icon: MapPin, mode: "pin" },
  { label: "Quick analysis: drop a pin and run", icon: Zap, mode: "quickpin" },
];

export default function LeftToolbar() {
  const drawMode = useMapStore((s) => s.drawMode);
  const setDrawMode = useMapStore((s) => s.setDrawMode);
  const setAoi = useMapStore((s) => s.setAoi);
  const aoi = useMapStore((s) => s.aoi);
  const aoiPolygon = useMapStore((s) => s.aoiPolygon);
  const [storiesOpen, setStoriesOpen] = useState(false);

  const button = (active: boolean) =>
    `h-10 w-10 grid place-items-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-amber/70 ${
      active ? "text-amber" : "text-dim hover:text-ink"
    }`;

  return (
    <>
      <nav
        aria-label="Area tools"
        className="absolute left-3 lg:left-5 top-20 lg:top-1/2 lg:-translate-y-1/2 z-30 flex flex-col items-center gap-2"
      >
        <div className="flex flex-col items-center rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel divide-y divide-line overflow-hidden">
          {TOOLS.map(({ label, icon: Icon, mode, tour }) => {
            const active = drawMode === mode;
            return (
              <button
                key={label}
                title={label}
                aria-label={label}
                aria-pressed={active}
                data-tour={tour}
                onClick={() => setDrawMode(mode === null || active ? null : (mode ?? null))}
                className={button(active)}
              >
                <Icon size={17} />
              </button>
            );
          })}
          {aoi && (
            <button
              title="Clear the area"
              aria-label="Clear the area"
              onClick={() => setAoi(null)}
              className={button(false)}
            >
              <Eraser size={17} />
            </button>
          )}
        </div>
        <div className="rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel overflow-hidden">
          <button
            title="Featured stories"
            aria-label="Featured stories"
            aria-expanded={storiesOpen}
            data-tour="stories"
            onClick={() => setStoriesOpen((v) => !v)}
            className={button(storiesOpen)}
          >
            <BookOpen size={17} />
          </button>
        </div>
        {aoi && (
          <div className="rounded-lg bg-surface/90 ring-1 ring-line px-2 py-1 font-mono text-[9px] text-dim text-center">
            {aoiAreaKm2(aoi, aoiPolygon).toLocaleString()}
            <br />
            km²
          </div>
        )}
      </nav>
      <AnimatePresence>
        {storiesOpen && (
          <StoriesMenu
            onClose={() => setStoriesOpen(false)}
            onPick={(story) => {
              setStoriesOpen(false);
              void playStory(story);
            }}
          />
        )}
      </AnimatePresence>
    </>
  );
}
