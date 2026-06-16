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
  stats: Record<string, unknown>;
}

export interface QueryResponse {
  understood: boolean;
  clarification: string | null;
  parameters: Record<string, unknown> | null;
  result: AnalysisResult | null;
  explanation: string | null;
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
