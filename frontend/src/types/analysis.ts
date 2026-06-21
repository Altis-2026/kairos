/** Mirrors the backend's /registry and /analyze response shapes. */

export interface AnalysisType {
  id: string;
  display_name: string;
  description: string;
  category: string;
  data_sources: string[];
  estimated_seconds: number;
  output_type: string;
  color_palette: string[];
  icon: string;
}

export interface HeadlineStat {
  label: string;
  value: number;
  unit: string;
}

export interface ContextLayer {
  id: string;
  name: string;
  tile_url: string;
  color: string;
  kind: string;
}

export interface AnalysisResult {
  analysis_type: string;
  display_name: string;
  bbox: [number, number, number, number];
  start_date: string;
  end_date: string;
  tile_url: string;
  data_date: string;
  confidence: number;
  headline_stat: HeadlineStat;
  context_layers?: ContextLayer[];
  stats: Record<string, unknown>;
}

export interface QueryResponse {
  understood: boolean;
  clarification: string | null;
  parameters: Record<string, unknown> | null;
  result: AnalysisResult | null;
  explanation: string | null;
}

/** Research views (backscatter / optical / compare / time-series). */
export interface ResearchLayerResponse {
  kind: string;
  tile_url: string;
  data_date: string;
  label: string;
  color: string;
  cloud_percent?: number;
}

export interface CompareComposite {
  tile_url: string;
  data_date: string;
  label: string;
}

export interface CompareResponse {
  polarization: string;
  before: CompareComposite;
  after: CompareComposite;
}

export interface TimeSeriesFrame {
  date: string;
  tile_url: string;
  value: number;
  label: string;
  unit: string;
}

export interface TimeSeriesResponse {
  frames: TimeSeriesFrame[];
  metric: string;
  unit: string;
}

/** Population & infrastructure impact for a detection footprint. */
export interface ImpactResponse {
  analysis_type: string;
  population_affected: number;
  built_up_km2: number;
  data_date: string;
  headline_stat: HeadlineStat;
}

export interface SceneInfo {
  scene_id: string;
  date: string;
  orbit_direction: string;
  instrument_mode: string;
  polarizations: string[];
}

export interface ScenesResponse {
  bbox: number[];
  start_date: string;
  end_date: string;
  scene_count: number;
  scenes: SceneInfo[];
}
