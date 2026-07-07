import { apiFetch } from "./client";
import type { BBox } from "../types/map";
import type { EventMarker, EventsResponse } from "../types/analysis";

export function fetchHistoricalEvents(p: {
  bbox: BBox;
  days?: number;
  category?: string;
  status?: "open" | "closed" | "all";
}): Promise<EventsResponse> {
  return apiFetch<EventsResponse>("/events/historical", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export function eventsToFeatureCollection(
  events: EventMarker[]
): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: events.map((e) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [e.lon, e.lat] },
      properties: {
        title: e.title,
        category: e.category,
        date: e.date,
        color: e.color,
        link: e.link ?? "",
      },
    })),
  };
}
