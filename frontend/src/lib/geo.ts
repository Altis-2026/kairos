import type { BBox } from "../types/map";

const EARTH_RADIUS_KM = 6371;

function toRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

export function haversineKm(a: [number, number], b: [number, number]): number {
  const dLat = toRad(b[1] - a[1]);
  const dLon = toRad(b[0] - a[0]);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a[1])) * Math.cos(toRad(b[1])) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(s));
}

export function polygonPerimeterKm(ring: [number, number][]): number {
  if (ring.length < 2) return 0;
  let total = 0;
  for (let i = 0; i < ring.length; i++) {
    total += haversineKm(ring[i], ring[(i + 1) % ring.length]);
  }
  return total;
}

export function polygonAreaKm2(ring: [number, number][]): number {
  if (ring.length < 3) return 0;
  let sum = 0;
  for (let i = 0; i < ring.length; i++) {
    const [lon1, lat1] = ring[i];
    const [lon2, lat2] = ring[(i + 1) % ring.length];
    sum += toRad(lon2 - lon1) * (2 + Math.sin(toRad(lat1)) + Math.sin(toRad(lat2)));
  }
  return Math.abs((sum * EARTH_RADIUS_KM * EARTH_RADIUS_KM) / 2);
}

export function bboxToRing(bbox: BBox): [number, number][] {
  const [minLon, minLat, maxLon, maxLat] = bbox;
  return [
    [minLon, minLat],
    [maxLon, minLat],
    [maxLon, maxLat],
    [minLon, maxLat],
  ];
}

export function polygonBBox(ring: [number, number][]): BBox {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  for (const [lon, lat] of ring) {
    minLon = Math.min(minLon, lon);
    minLat = Math.min(minLat, lat);
    maxLon = Math.max(maxLon, lon);
    maxLat = Math.max(maxLat, lat);
  }
  return [minLon, minLat, maxLon, maxLat];
}

export function aoiAreaKm2(bbox: BBox, polygon: [number, number][] | null): number {
  return Math.round(polygonAreaKm2(polygon ?? bboxToRing(bbox)));
}

export function aoiPerimeterKm(bbox: BBox, polygon: [number, number][] | null): number {
  return Math.round(polygonPerimeterKm(polygon ?? bboxToRing(bbox)));
}
