export type BBox = [number, number, number, number]; // [minLon, minLat, maxLon, maxLat]

export interface RasterLayer {
  id: string;
  name: string;
  tileUrl: string;
  opacity: number;
  visible: boolean;
  color: string;
  // Layers belonging to a research control are driven by that control's UI
  // (compare slider / timeline scrubber) and hidden from the normal LayerPanel.
  group?: "compare" | "timeline";
}

/** A pointer to the most recent analysis, so research tools can act on it. */
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

export type DrawMode = "rectangle" | "pin" | "quickpin" | null;

export type BaseStyle = "satellite" | "dark" | "terrain";

export type Projection = "globe" | "mercator";
