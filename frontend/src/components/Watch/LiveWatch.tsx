import { useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Loader2, Radio, RefreshCw, Sparkles, X } from "lucide-react";
import Globe from "../Globe";
import WatchEventDetail from "./WatchEventDetail";
import { useMapStore } from "../../stores/mapStore";
import { fetchHistoricalEvents, eventsToFeatureCollection } from "../../api/events";
import {
  ANALYSIS_COLORS,
  fetchFeed,
  timeAgo,
  triggerSweep,
  type FeedResponse,
  type Finding,
} from "../../api/feed";
import { buildShareUrl } from "../../lib/share";
import { goToApp } from "../../lib/embed";
import type { EventMarker } from "../../types/analysis";

const WATCH_LAYER = "livewatch-events";
const FINDINGS_LAYER = "livewatch-findings";
const WORLD: [number, number, number, number] = [-179, -82, 179, 82];

type Status = "loading" | "ok" | "empty" | "unavailable";
type Tab = "findings" | "events";

function findingsToFeatureCollection(findings: Finding[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: findings.map((f) => ({
      type: "Feature",
      properties: { color: ANALYSIS_COLORS[f.analysis_type] ?? "#00BFA8" },
      geometry: {
        type: "Point",
        coordinates: [
          (f.bbox[0] + f.bbox[2]) / 2,
          (f.bbox[1] + f.bbox[3]) / 2,
        ],
      },
    })),
  };
}

function openFinding(f: Finding) {
  const url = buildShareUrl({
    analysis_type: f.analysis_type,
    bbox: f.bbox,
    start_date: f.start_date,
    end_date: f.end_date,
  });
  location.href = url;
  location.reload();
}

export default function LiveWatch() {
  const [tab, setTab] = useState<Tab>("findings");
  const [events, setEvents] = useState<EventMarker[]>([]);
  const [eventStatus, setEventStatus] = useState<Status>("loading");
  const [note, setNote] = useState<string | null>(null);
  const [selected, setSelected] = useState<EventMarker | null>(null);
  const [feed, setFeed] = useState<FeedResponse | null>(null);
  const [feedStatus, setFeedStatus] = useState<Status>("loading");
  const [sweepRequested, setSweepRequested] = useState(false);
  const home = `${location.origin}${location.pathname}#app`;

  function loadFeed() {
    fetchFeed(40)
      .then((d) => {
        setFeed(d);
        setFeedStatus(d.findings.length ? "ok" : "empty");
        if (d.findings.length) {
          useMapStore.getState().addPointLayer({
            id: FINDINGS_LAYER,
            name: "Kairos findings",
            data: findingsToFeatureCollection(d.findings),
            color: "#00BFA8",
            visible: true,
          });
        }
      })
      .catch(() => setFeedStatus("unavailable"));
  }

  useEffect(() => {
    loadFeed();
    let cancelled = false;
    fetchHistoricalEvents({ bbox: WORLD, days: 60, status: "open" })
      .then((d) => {
        if (cancelled) return;
        if (!d.available) {
          setEventStatus("unavailable");
          setNote(d.note ?? "Live feed unavailable.");
          return;
        }
        if (!d.events.length) {
          setEventStatus("empty");
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
        setEventStatus("ok");
      })
      .catch(() => {
        if (cancelled) return;
        setEventStatus("unavailable");
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

  function flyToFinding(f: Finding) {
    useMapStore
      .getState()
      .requestFlyTo([(f.bbox[0] + f.bbox[2]) / 2, (f.bbox[1] + f.bbox[3]) / 2], 6);
  }

  async function requestSweep() {
    setSweepRequested(true);
    try {
      await triggerSweep();
      setTimeout(loadFeed, 45000);
    } catch {
      setSweepRequested(false);
    }
  }

  const tabButton = (id: Tab, label: string) => (
    <button
      onClick={() => setTab(id)}
      className={`flex-1 h-8 rounded-lg text-[11px] font-medium transition-colors ${
        tab === id ? "bg-raised text-teal ring-1 ring-teal/40" : "text-dim hover:text-ink"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="relative h-full w-full bg-bg overflow-hidden">
      <Globe />

      <div className="absolute left-3 sm:left-5 top-3 sm:top-5 z-30 flex items-center gap-2.5 rounded-2xl bg-surface/90 backdrop-blur ring-1 ring-line shadow-panel px-4 py-2.5">
        <Radio size={16} className="text-amber animate-pulse" />
        <div>
          <div className="font-display text-lg text-ink leading-none">
            Kairos <span className="text-teal">Live Watch</span>
          </div>
          <div className="font-mono text-[10px] tracking-[0.18em] text-dim mt-0.5">
            AUTONOMOUS SWEEP · NASA EONET
          </div>
        </div>
      </div>

      <aside className="absolute z-30 max-sm:inset-x-3 max-sm:bottom-3 max-sm:max-h-[55dvh] sm:right-5 sm:top-1/2 sm:-translate-y-1/2 sm:w-[340px] sm:max-h-[82vh] rounded-2xl bg-surface/95 backdrop-blur ring-1 ring-line shadow-panel p-4 space-y-3 overflow-hidden flex flex-col">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] tracking-[0.2em] text-dim">
            {tab === "findings"
              ? `${feed?.findings.length ?? 0} AUTONOMOUS FINDINGS`
              : `${events.length} ACTIVE EVENTS`}
          </span>
          <a href={home} onClick={goToApp} className="text-dim hover:text-ink" title="Exit Live Watch">
            <X size={15} />
          </a>
        </div>

        <div className="flex gap-1.5 rounded-xl bg-bg/70 ring-1 ring-line p-1">
          {tabButton("findings", "Kairos found this")}
          {tabButton("events", "Active events")}
        </div>

        {tab === "findings" ? (
          <>
            {feedStatus === "loading" ? (
              <div className="flex items-center gap-2 text-xs text-dim">
                <Loader2 size={14} className="animate-spin" /> Loading findings…
              </div>
            ) : feedStatus === "unavailable" ? (
              <p className="text-[11px] text-dim leading-relaxed">
                The findings feed is unreachable right now. It comes back
                automatically once the Kairos API is up.
              </p>
            ) : feedStatus === "empty" ? (
              <div className="space-y-2">
                <p className="text-[11px] text-dim leading-relaxed">
                  No findings yet. Kairos sweeps its watchlist and active
                  disasters every {feed?.interval_hours ?? 6} hours and posts
                  what it detects here, without being asked.
                </p>
                <button
                  onClick={requestSweep}
                  disabled={sweepRequested || feed?.sweeping}
                  className="w-full h-9 rounded-xl text-xs ring-1 ring-teal/40 text-teal hover:bg-raised transition disabled:opacity-50"
                >
                  {feed?.sweeping || sweepRequested
                    ? "Sweeping now… results in a few minutes"
                    : "Run a sweep now"}
                </button>
              </div>
            ) : (
              <ul className="space-y-1.5 overflow-y-auto">
                {feed?.findings.map((f) => (
                  <li key={f.id}>
                    <div
                      onClick={() => flyToFinding(f)}
                      className="rounded-xl bg-bg/70 ring-1 ring-line hover:ring-teal/40 p-2.5 transition cursor-pointer"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2 w-2 rounded-full shrink-0"
                          style={{
                            background: ANALYSIS_COLORS[f.analysis_type] ?? "#00BFA8",
                          }}
                        />
                        <span className="text-[11px] text-ink truncate flex-1">
                          {f.region}
                        </span>
                        {f.headline_value != null && (
                          <span className="font-mono text-[10px] text-teal shrink-0">
                            {Math.round(f.headline_value).toLocaleString()}{" "}
                            {f.headline_unit}
                          </span>
                        )}
                      </div>
                      {f.summary && (
                        <p className="text-[10px] text-dim leading-snug mt-1 pl-4 line-clamp-3">
                          {f.summary}
                        </p>
                      )}
                      <div className="flex items-center justify-between mt-1.5 pl-4">
                        <span className="font-mono text-[9px] text-dim">
                          {f.display_name}
                          {f.data_date && ` · pass ${f.data_date}`} ·{" "}
                          {timeAgo(f.created_at)}
                        </span>
                        <button
                          onClick={(ev) => {
                            ev.stopPropagation();
                            openFinding(f);
                          }}
                          className="font-mono text-[9px] text-teal hover:underline shrink-0"
                        >
                          VIEW →
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {feedStatus === "ok" && feed?.last_sweep?.finished_at && (
              <div className="flex items-center justify-between font-mono text-[9px] text-dim pt-1 border-t border-line">
                <span>
                  Last sweep {timeAgo(feed.last_sweep.finished_at)}
                  {feed.next_sweep_at &&
                    ` · next ${new Date(feed.next_sweep_at * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`}
                </span>
                <button
                  onClick={loadFeed}
                  title="Refresh findings"
                  className="text-dim hover:text-teal transition-colors"
                >
                  <RefreshCw size={11} />
                </button>
              </div>
            )}
          </>
        ) : eventStatus === "loading" ? (
          <div className="flex items-center gap-2 text-xs text-dim">
            <Loader2 size={14} className="animate-spin" /> Scanning the planet…
          </div>
        ) : eventStatus === "unavailable" ? (
          <p className="text-[11px] text-dim leading-relaxed">
            {note} The dashboard populates automatically wherever outbound access
            to <span className="font-mono text-teal">eonet.gsfc.nasa.gov</span> is
            allowed.
          </p>
        ) : eventStatus === "empty" ? (
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

      <div className="absolute left-3 sm:left-5 bottom-3 sm:bottom-5 z-20 hidden sm:flex items-center gap-2 rounded-full bg-surface/80 backdrop-blur ring-1 ring-line px-3 py-1.5 font-mono text-[10px] text-dim">
        <Sparkles size={11} className="text-teal" />
        Findings are generated by Kairos on its own schedule, no user asked for them
      </div>

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
