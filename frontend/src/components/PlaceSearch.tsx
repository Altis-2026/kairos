import { useEffect, useRef, useState } from "react";
import { Loader2, MapPin, Search } from "lucide-react";
import { locatePlace } from "../api/myplace";
import type { BBox } from "../types/map";

const MAPBOX_TOKEN = (import.meta.env.VITE_MAPBOX_TOKEN as string) || "";

const HALF_LON = 0.06;
const HALF_LAT = 0.045;

export interface PickedPlace {
  label: string;
  lon: number;
  lat: number;
  bbox: BBox;
}

interface Hit {
  id: string;
  label: string;
  lon: number;
  lat: number;
}

function bboxAround(lon: number, lat: number): BBox {
  return [
    +(lon - HALF_LON).toFixed(5),
    +(lat - HALF_LAT).toFixed(5),
    +(lon + HALF_LON).toFixed(5),
    +(lat + HALF_LAT).toFixed(5),
  ];
}

export default function PlaceSearch({
  onPick,
  placeholder = "Address, city or ZIP",
  ariaLabel = "Address",
  autoFocus = false,
}: {
  onPick: (place: PickedPlace) => void;
  placeholder?: string;
  ariaLabel?: string;
  autoFocus?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [error, setError] = useState<string | null>(null);
  const justPicked = useRef(false);

  useEffect(() => {
    if (justPicked.current) {
      justPicked.current = false;
      return;
    }
    const q = query.trim();
    if (q.length < 3 || !MAPBOX_TOKEN) {
      setHits([]);
      setOpen(false);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(
          `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(
            q
          )}.json?access_token=${MAPBOX_TOKEN}&limit=5&autocomplete=true&types=address,place,postcode,locality,neighborhood`,
          { signal: controller.signal }
        );
        const data = await res.json();
        const next: Hit[] = (data.features ?? [])
          .filter((f: { center?: number[] }) => Array.isArray(f.center))
          .map((f: { id: string; place_name: string; center: number[] }) => ({
            id: f.id,
            label: f.place_name,
            lon: f.center[0],
            lat: f.center[1],
          }));
        setHits(next);
        setActiveIndex(-1);
        setOpen(next.length > 0);
      } catch {

      }
    }, 250);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [query]);

  function choose(hit: Hit) {
    justPicked.current = true;
    setQuery(hit.label);
    setOpen(false);
    setHits([]);
    setError(null);
    onPick({
      label: hit.label,
      lon: hit.lon,
      lat: hit.lat,
      bbox: bboxAround(hit.lon, hit.lat),
    });
  }

  // Typing a full address and pressing Enter without touching the list should
  // still work, so fall back to the backend geocoder when there is no hit.
  async function submitRaw() {
    const q = query.trim();
    if (q.length < 3 || busy) return;
    if (hits.length) {
      choose(hits[activeIndex >= 0 ? activeIndex : 0]);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const hit = await locatePlace(q);
      if (!hit.found || !hit.bbox || hit.lon == null || hit.lat == null) {
        setError("That place did not match anywhere. Try adding a city or ZIP.");
      } else {
        justPicked.current = true;
        setOpen(false);
        onPick({
          label: hit.label ?? q,
          lon: hit.lon,
          lat: hit.lat,
          bbox: hit.bbox,
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Address lookup failed.");
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (open && hits.length) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => (i + 1) % hits.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => (i <= 0 ? hits.length - 1 : i - 1));
        return;
      }
      if (e.key === "Escape") {
        setOpen(false);
        return;
      }
    }
    if (e.key === "Enter") {
      e.preventDefault();
      void submitRaw();
    }
  }

  return (
    <div className="space-y-1.5">
      <div className="relative">
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            onFocus={() => hits.length && setOpen(true)}
            placeholder={placeholder}
            aria-label={ariaLabel}
            autoFocus={autoFocus}
            autoComplete="off"
            className="flex-1 h-10 rounded-xl bg-bg/70 ring-1 ring-line px-3 text-xs text-ink placeholder-dim outline-none focus:ring-amber/60"
          />
          <button
            onClick={submitRaw}
            disabled={busy}
            title="Find this place"
            aria-label="Find this place"
            className="h-10 w-10 grid place-items-center rounded-xl bg-amber text-bg hover:brightness-110 transition disabled:opacity-50"
          >
            {busy ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Search size={14} />
            )}
          </button>
        </div>

        {open && hits.length > 0 && (
          <ul className="absolute top-11 inset-x-0 z-50 max-h-56 overflow-y-auto rounded-xl bg-surface ring-1 ring-line shadow-panel py-1">
            {hits.map((hit, i) => (
              <li key={hit.id}>
                <button
                  onMouseDown={(e) => {
                    e.preventDefault();
                    choose(hit);
                  }}
                  onMouseEnter={() => setActiveIndex(i)}
                  className={`w-full text-left flex items-start gap-2 px-3 py-2 text-[11px] leading-snug transition-colors ${
                    i === activeIndex
                      ? "bg-raised text-ink"
                      : "text-dim hover:text-ink"
                  }`}
                >
                  <MapPin size={11} className="shrink-0 text-teal mt-0.5" />
                  <span>{hit.label}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {error && <p className="text-[11px] text-amber leading-snug">{error}</p>}
    </div>
  );
}
