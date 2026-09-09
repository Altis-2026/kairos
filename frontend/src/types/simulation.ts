/** Mirrors the backend's flood-simulation payload (backend/solver/payload.py). */

/** Everything the viewer needs about one solve, minus the arrays themselves. */
export interface SimulationMeta {
  ny: number;
  nx: number;
  dx: number;
  times: number[];
  n_frames: number;
  dem_min: number;
  dem_max: number;
  /** Peak depth in the frames actually shipped — what the animation shows. */
  depth_max: number;
  /** Peak depth the solver computed. Equal to depth_max at native resolution. */
  depth_max_solve: number;
  decimated: boolean;
  transport_factor: number;
  solve_dx: number;
  solve_shape: number[];
  depth_units: string;
  dem_units: string;

  /** Always "simulated". Never render this payload without saying so. */
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

/** The raw payload as it arrives over the wire. */
export interface SimulationPayload {
  meta: SimulationMeta;
  dem_b64: string;
  depth_b64: string;
}

/** A payload after decoding, ready to render. */
export interface DecodedSimulation {
  meta: SimulationMeta;
  /** (ny * nx) terrain elevation in metres. */
  dem: Float32Array;
  /** (n_frames * ny * nx) depth in centimetres, frame-major. */
  depths: Uint16Array;
  ny: number;
  nx: number;
  frames: number;
  times: number[];
  /** Peak depth in centimetres — the ramp's top stop. */
  peakCm: number;
}
