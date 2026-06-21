export type BBox = [number, number, number, number]; // [minLon, minLat, maxLon, maxLat]

export interface RasterLayer {
  id: string;
  name: string;
  tileUrl: string;
  opacity: number;
  visible: boolean;
  color: string;
}

export interface PointLayer {
  id: string;
  name: string;
  data: GeoJSON.FeatureCollection;
  color: string;
  visible: boolean;
}

export type DrawMode = "rectangle" | "pin" | "quickpin" | null;

export type BaseStyle = "satellite" | "dark" | "terrain";

export type Projection = "globe" | "mercator";
