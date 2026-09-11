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

// ---------------------------------------------------------------------------
// Wildfire (backend/solver/fire_sim.py)
// ---------------------------------------------------------------------------

/**
 * A fire ships one arrival-time grid, not a stack of frames.
 *
 * Every instant of the animation is a threshold of the same array, so the
 * viewer can render any moment rather than stepping between precomputed
 * frames — smaller over the wire and smoother on screen.
 */
export interface FireMeta {
  ny: number;
  nx: number;
  dx: number;
  duration_min: number;
  /** uint16 sentinel meaning "the fire never got here". */
  arrival_unburned: number;
  arrival_units: string;
  /** Flame length is stored as decimetres; divide by this for metres. */
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

  /** Always "simulated". Never render this payload without saying so. */
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
  /** (ny * nx) terrain elevation in metres. */
  dem: Float32Array;
  /** (ny * nx) arrival time in minutes; `unburned` where it never reached. */
  arrival: Uint16Array;
  /** (ny * nx) flame length in decimetres at the moment the front passed. */
  flame: Uint16Array;
  ny: number;
  nx: number;
  /** The sentinel value, lifted out of meta so render loops need not reach. */
  unburned: number;
  durationMin: number;
  /** Synthetic frame count, so one scrubber drives both kinds of solve. */
  frames: number;
  /** Minutes at each synthetic frame. */
  times: number[];
}

/**
 * Either forward model's solve.
 *
 * The two share every field the 3D viewer needs to build its scene — grid
 * dimensions, the DEM, cell size, elevation range, the AOI box — and differ
 * only in the surface draped over it. That is why the viewer takes this union
 * rather than one of each: the mesh, the camera and the basemap are written
 * once. `DecodedFire` carries a `kind` discriminant; a flood solve has none,
 * so the absence of it is what identifies a flood.
 */
export type AnySolve = DecodedSimulation | DecodedFire;

export function isFire(solve: AnySolve | null): solve is DecodedFire {
  return (solve as DecodedFire | null)?.kind === "fire";
}
