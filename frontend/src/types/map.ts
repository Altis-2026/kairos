export type BBox = [number, number, number, number];

export interface RasterLayer {
  id: string;
  name: string;
  tileUrl: string;
  opacity: number;
  visible: boolean;
  color: string;

  group?: "compare" | "timeline";
}

export interface ResultRef {
  analysisType: string;
  displayName: string;
  bbox: BBox;
  startDate: string;
  endDate: string;
  dataDate: string;
  confidence: number;
  headlineLabel: string;
  headlineValue: number;
  headlineUnit: string;
  stats?: Record<string, unknown>;
}

export interface CompareControl {
  beforeLayerId: string;
  afterLayerId: string;
  beforeLabel: string;
  afterLabel: string;
}

export interface TimelineFrame {
  layerId: string;
  date: string;
  value: number;
}

export interface TimelineControl {
  frames: TimelineFrame[];
  unit: string;
  metric: string;
}

export interface PointLayer {
  id: string;
  name: string;
  data: GeoJSON.FeatureCollection;
  color: string;
  visible: boolean;
}

export type DrawMode = "rectangle" | "polygon" | "pin" | "quickpin" | null;

export type BaseStyle = "satellite" | "dark" | "terrain";

export type Projection = "globe" | "mercator";
