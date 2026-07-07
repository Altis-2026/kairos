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
  results: AnalysisResult[] | null;
  explanation: string | null;
}

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

export interface AlertCheckResponse {
  new: boolean;
  data_date: string | null;
  checked_at: string;
  note?: string;
  headline_stat?: HeadlineStat;
  result: AnalysisResult | null;
}

export interface EventMarker {
  id: string;
  title: string;
  category: string;
  category_id: string;
  color: string;
  date: string;
  lon: number;
  lat: number;
  closed: boolean;
  link: string | null;
}

export interface EventsResponse {
  available: boolean;
  events: EventMarker[];
  count?: number;
  source: string;
  note?: string;
}

export interface InterpretResponse {
  available: boolean;
  text: string;
  source?: "ai" | "template" | "web";
  note?: string;
}

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
