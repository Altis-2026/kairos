import type { EventMarker } from "../types/analysis";
import type { BBox } from "../types/map";

interface WatchPlan {
  analysisType: string;

  pitch: string;
}

const CATEGORY_PLAN: Record<string, WatchPlan> = {
  wildfires: {
    analysisType: "wildfire_burn_scar",
    pitch: "Map the burn scar straight through the smoke that blinds optical satellites.",
  },
  floods: {
    analysisType: "flood_extent",
    pitch: "Map the water's reach. Radar sees flooding through storm cloud, day or night.",
  },
  severeStorms: {
    analysisType: "flood_extent",
    pitch: "Map storm-surge and rain flooding under the cloud deck.",
  },
  seaLakeIce: {
    analysisType: "sea_ice",
    pitch: "Trace the ice edge through the polar dark.",
  },
  landslides: {
    analysisType: "surface_deformation",
    pitch: "Flag where the ground surface has changed and slid.",
  },
  earthquakes: {
    analysisType: "building_damage",
    pitch: "Triage likely building damage within hours, through dust and cloud.",
  },
  volcanoes: {
    analysisType: "surface_deformation",
    pitch: "Flag fresh ground change around the vent.",
  },
  manmade: {
    analysisType: "land_disturbance",
    pitch: "Surface land clearing and disturbance for review.",
  },
  waterColor: {
    analysisType: "oil_spill",
    pitch: "Look for slicks that flatten the ocean's radar return.",
  },
};

const DEFAULT_PLAN: WatchPlan = {
  analysisType: "surface_deformation",
  pitch: "Flag how this area's surface has changed recently.",
};

export function planForEvent(event: EventMarker): WatchPlan {
  return CATEGORY_PLAN[event.category_id] ?? DEFAULT_PLAN;
}

export function eventBbox(event: EventMarker, halfDeg = 0.25): BBox {
  return [
    event.lon - halfDeg,
    event.lat - halfDeg,
    event.lon + halfDeg,
    event.lat + halfDeg,
  ];
}

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function eventWindow(event: EventMarker): {
  start_date: string;
  end_date: string;
} {
  const today = new Date();
  const end = new Date(today);
  end.setDate(end.getDate());

  const thirtyAgo = new Date(today);
  thirtyAgo.setDate(thirtyAgo.getDate() - 30);

  const onset = event.date ? new Date(event.date) : thirtyAgo;

  let start = onset > thirtyAgo ? onset : thirtyAgo;
  const dayBefore = new Date(end);
  dayBefore.setDate(dayBefore.getDate() - 2);
  if (start >= dayBefore) start = thirtyAgo;

  return { start_date: iso(start), end_date: iso(end) };
}
