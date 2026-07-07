import { useState } from "react";
import { AlertTriangle, Eye, EyeOff, Loader2, Trash2, X } from "lucide-react";
import { motion } from "framer-motion";
import { useMapStore } from "../../stores/mapStore";
import { fetchHistoricalEvents, eventsToFeatureCollection } from "../../api/events";

const EVENTS_LAYER_ID = "historical-events";

export default function LayerPanel({ onClose }: { onClose: () => void }) {

  const layers = useMapStore((s) => s.layers.filter((l) => !l.group));
  const pointLayers = useMapStore((s) => s.pointLayers);
  const baseStyle = useMapStore((s) => s.baseStyle);
  const setBaseStyle = useMapStore((s) => s.setBaseStyle);
  const toggleLayerVisible = useMapStore((s) => s.toggleLayerVisible);
  const setLayerOpacity = useMapStore((s) => s.setLayerOpacity);
  const removeLayer = useMapStore((s) => s.removeLayer);

  const eventsOn = pointLayers.some((l) => l.id === EVENTS_LAYER_ID);
  const [eventsBusy, setEventsBusy] = useState(false);
  const [eventsNote, setEventsNote] = useState<string | null>(null);

  async function toggleHistoricalEvents() {
    const map = useMapStore.getState();
    if (eventsOn) {
      map.removeLayer(EVENTS_LAYER_ID);
      setEventsNote(null);
      return;
    }
    const bbox = map.viewportBbox;
    if (!bbox) {
      setEventsNote("Move the globe to set a view first.");
      return;
    }
    setEventsBusy(true);
    setEventsNote(null);
    try {
      const data = await fetchHistoricalEvents({ bbox, days: 3650 });
      if (!data.available) {
        setEventsNote(data.note ?? "Events feed unavailable right now.");
        return;
      }
      if (data.events.length === 0) {
        setEventsNote("No recorded disasters in this view (last ~10 years).");
        return;
      }
      map.addPointLayer({
        id: EVENTS_LAYER_ID,
        name: `Historical disasters (${data.events.length})`,
        data: eventsToFeatureCollection(data.events),
        color: "#E8A318",
        visible: true,
      });
      setEventsNote(`${data.events.length} events · click a marker for detail.`);
    } catch (e) {
      setEventsNote(e instanceof Error ? e.message : "Could not load events.");
    } finally {
      setEventsBusy(false);
    }
  }

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-24 max-sm:max-h-[58dvh] sm:right-20 sm:top-1/2 sm:-translate-y-1/2 sm:w-80 sm:max-h-[82vh] overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
          LAYERS
        </span>
        <button onClick={onClose} className="text-dim hover:text-ink" title="Close">
          <X size={15} />
        </button>
      </div>

      <div className="flex gap-2">
        {(["satellite", "dark", "terrain"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setBaseStyle(s)}
            className={`flex-1 h-9 rounded-lg text-xs capitalize transition ring-1 ${
              baseStyle === s
                ? "bg-raised text-teal ring-teal/50"
                : "text-dim ring-line hover:text-ink"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="space-y-1.5">
        <button
          onClick={toggleHistoricalEvents}
          disabled={eventsBusy}
          className={`w-full flex items-center gap-2.5 rounded-xl ring-1 px-3 py-2.5 text-left transition disabled:opacity-60 ${
            eventsOn
              ? "bg-raised text-amber ring-amber/50"
              : "bg-bg/70 text-dim ring-line hover:text-ink"
          }`}
          title="Show past floods, fires and storms near this view (NASA EONET)"
        >
          <span className={eventsOn ? "text-amber" : "text-dim"}>
            {eventsBusy ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <AlertTriangle size={14} />
            )}
          </span>
          <span className="min-w-0">
            <span className="block text-xs text-ink">Historical disasters</span>
            <span className="block text-[10px] text-dim leading-tight">
              Past events in view · NASA EONET
            </span>
          </span>
          <span
            className={`ml-auto font-mono text-[9px] tracking-wider ${
              eventsOn ? "text-amber" : "text-dim"
            }`}
          >
            {eventsOn ? "ON" : "OFF"}
          </span>
        </button>
        {eventsNote && (
          <p className="text-[10px] text-dim leading-snug px-1">{eventsNote}</p>
        )}
      </div>

      {layers.length === 0 ? (
        <p className="text-xs text-dim leading-relaxed">
          No analysis layers yet. Run an analysis from the sidebar or ask a
          question below. Results appear here.
        </p>
      ) : (
        <ul className="space-y-3 max-h-72 overflow-y-auto">
          {layers.map((l) => (
            <li key={l.id} className="rounded-xl bg-bg/70 ring-1 ring-line p-3 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 text-xs text-ink truncate">
                  <span
                    className="h-2 w-2 rounded-full shrink-0"
                    style={{ background: l.color }}
                  />
                  {l.name}
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  <button
                    onClick={() => toggleLayerVisible(l.id)}
                    className="text-dim hover:text-ink"
                    title={l.visible ? "Hide layer" : "Show layer"}
                  >
                    {l.visible ? <Eye size={14} /> : <EyeOff size={14} />}
                  </button>
                  <button
                    onClick={() => removeLayer(l.id)}
                    className="text-dim hover:text-ink"
                    title="Remove layer"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={l.opacity}
                onChange={(e) => setLayerOpacity(l.id, Number(e.target.value))}
                className="w-full accent-teal h-1"
                title="Layer opacity"
              />
            </li>
          ))}
        </ul>
      )}
    </motion.aside>
  );
}
