export interface SimulationMeta {
  ny: number;
  nx: number;
  dx: number;
  times: number[];
  n_frames: number;
  dem_min: number;
  dem_max: number;

  depth_max: number;

  depth_max_solve: number;
  decimated: boolean;
  transport_factor: number;
  solve_dx: number;
  solve_shape: number[];
  depth_units: string;
  dem_units: string;

  mode: string;
  disclosure?: string;
  scene_id?: string | null;
  scene_name?: string | null;
  bbox?: number[];
  event_date?: string;
  wet_threshold_m?: number;

  steps?: number;
  truncated?: boolean;
  truncation_reason?: string | null;
  limiter_activations?: number;
  open_edges?: string[];
  pits_filled?: boolean;
  volume?: Record<string, number>;
}

export interface SimulationPayload {
  meta: SimulationMeta;
  dem_b64: string;
  depth_b64: string;
}

export interface DecodedSimulation {
  meta: SimulationMeta;

  dem: Float32Array;

  depths: Uint16Array;
  ny: number;
  nx: number;
  frames: number;
  times: number[];

  peakCm: number;
}

export interface FireMeta {
  ny: number;
  nx: number;
  dx: number;
  duration_min: number;

  arrival_unburned: number;
  arrival_units: string;

  flame_scale: number;
  flame_units: string;
  dem_units: string;
  dem_min: number;
  dem_max: number;
  flame_max_m: number;
  burned_cells: number;
  fuel_model: string;
  fuel_name: string;
  wind_ms?: number;
  wind_from_bearing?: number;

  mode: string;
  disclosure?: string;
  scene_id?: string | null;
  scene_name?: string | null;
  bbox?: number[];
  event_date?: string;
}

export interface FirePayload {
  meta: FireMeta;
  dem_b64: string;
  arrival_b64: string;
  flame_b64: string;
}

export interface DecodedFire {
  kind: "fire";
  meta: FireMeta;

  dem: Float32Array;

  arrival: Uint16Array;

  flame: Uint16Array;
  ny: number;
  nx: number;

  unburned: number;
  durationMin: number;

  frames: number;

  times: number[];
}

export type AnySolve = DecodedSimulation | DecodedFire;

export function isFire(solve: AnySolve | null): solve is DecodedFire {
  return (solve as DecodedFire | null)?.kind === "fire";
}
