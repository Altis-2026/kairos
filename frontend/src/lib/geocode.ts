import type { BBox } from "../types/map";

const TOKEN = (import.meta.env.VITE_MAPBOX_TOKEN as string) || "";

export async function reverseGeocodeBbox(bbox: BBox): Promise<string | undefined> {
  if (!TOKEN) return undefined;
  const lng = (bbox[0] + bbox[2]) / 2;
  const lat = (bbox[1] + bbox[3]) / 2;
  try {
    const res = await fetch(
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json` +
        `?access_token=${TOKEN}&types=place,region,country&limit=1`
    );
    if (!res.ok) return undefined;
    const data = await res.json();
    return (data.features?.[0]?.place_name as string) || undefined;
  } catch {
    return undefined;
  }
}
