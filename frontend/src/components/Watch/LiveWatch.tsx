import { useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Loader2, Radio, X } from "lucide-react";
import Globe from "../Globe";
import WatchEventDetail from "./WatchEventDetail";
import { useMapStore } from "../../stores/mapStore";
import { fetchHistoricalEvents, eventsToFeatureCollection } from "../../api/events";
import { goToApp } from "../../lib/embed";
import type { EventMarker } from "../../types/analysis";

const WATCH_LAYER = "livewatch-events";
const WORLD: [number, number, number, number] = [-179, -82, 179, 82];

type Status = "loading" | "ok" | "empty" | "unavailable";

export default function LiveWatch() {
  const [events, setEvents] = useState<EventMarker[]>([]);
  const [status, setStatus] = useState<Status>("loading");
  const [note, setNote] = useState<string | null>(null);
  const [selected, setSelected] = useState<EventMarker | null>(null);
  const home = `${location.origin}${location.pathname}#app`;

  useEffect(() => {
    let cancelled = false;
    fetchHistoricalEvents({ bbox: WORLD, days: 60, status: "open" })
      .then((d) => {
        if (cancelled) return;
        if (!d.available) {
          setStatus("unavailable");
          setNote(d.note ?? "Live feed unavailable.");
          return;
        }
        if (!d.events.length) {
          setStatus("empty");
          return;
        }
        setEvents(d.events);
        useMapStore.getState().addPointLayer({
          id: WATCH_LAYER,
          name: "Active disasters",
          data: eventsToFeatureCollection(d.events),
          color: "#E8A318",
          visible: true,
        });
        setStatus("ok");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("unavailable");
        setNote("Live feed unavailable right now.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function flyTo(e: EventMarker) {
    useMapStore.getState().requestFlyTo([e.lon, e.lat], 5);
    setSelected(e);
  }

  return (
    <div className="relative h-full w-full bg-bg overflow-hidden">
      <Globe />

      <div className="absolute left-5 top-5 z-30 flex items-center gap-2.5 rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel px-4 py-2.5">
        <Radio size={16} className="text-amber animate-pulse" />
        <div>
          <div className="font-display text-lg text-ink leading-none">
            Kairos <span className="text-teal">Live Watch</span>
          </div>
          <div className="font-mono text-[10px] tracking-[0.18em] text-dim mt-0.5">
            ACTIVE NATURAL DISASTERS · NASA EONET
          </div>
        </div>
      </div>

      <aside className="absolute right-5 top-1/2 -translate-y-1/2 z-30 w-80 max-h-[80vh] rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-3 overflow-hidden flex flex-col">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
            {status === "ok" ? `${events.length} ACTIVE EVENTS` : "LIVE WATCH"}
          </span>
          <a href={home} onClick={goToApp} className="text-dim hover:text-ink" title="Exit Live Watch">
            <X size={15} />
          </a>
        </div>

        {status === "loading" ? (
          <div className="flex items-center gap-2 text-xs text-dim">
            <Loader2 size={14} className="animate-spin" /> Scanning the planet…
          </div>
        ) : status === "unavailable" ? (
          <p className="text-[11px] text-dim leading-relaxed">
            {note} The dashboard populates automatically wherever outbound access
            to <span className="font-mono text-teal">eonet.gsfc.nasa.gov</span> is
            allowed.
          </p>
        ) : status === "empty" ? (
          <p className="text-[11px] text-dim leading-relaxed">
            No active tracked disasters right now. Check back later.
          </p>
        ) : (
          <ul className="space-y-1.5 overflow-y-auto">
            {events.map((e) => (
              <li key={e.id}>
                <button
                  onClick={() => flyTo(e)}
                  className={`w-full text-left rounded-xl bg-bg/70 ring-1 p-2.5 transition ${
                    selected?.id === e.id
                      ? "ring-teal/60"
                      : "ring-line hover:ring-teal/40"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full shrink-0"
                      style={{ background: e.color }}
                    />
                    <span className="text-[11px] text-ink truncate">{e.title}</span>
                  </div>
                  <div className="font-mono text-[9px] text-dim mt-0.5 pl-4">
                    {e.category}
                    {e.date && ` · ${e.date}`}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}

        <a
          href={home}
          onClick={goToApp}
          className="mt-auto block text-center h-9 rounded-xl text-xs ring-1 ring-line text-dim hover:text-teal hover:ring-teal/40 transition leading-9"
        >
          Open the full Kairos workspace →
        </a>
      </aside>

      <AnimatePresence>
        {selected && (
          <WatchEventDetail
            event={selected}
            onClose={() => setSelected(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
