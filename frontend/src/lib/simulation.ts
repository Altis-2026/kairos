/**
 * Decode and colourise a flood simulation for display.
 *
 * The backend ships two typed arrays as base64: terrain as float32 metres and
 * depth frames as uint16 centimetres, frame-major. This module turns those
 * into pixels. It is deliberately pure — no Mapbox, no React — so the colour
 * ramp and the depth mapping can be checked on their own.
 *
 * Colour ramp
 * -----------
 * Depth runs shallow-to-deep through cyan, blue, indigo, magenta. Two
 * decisions matter more than the hues:
 *
 *   * Alpha ramps with depth as well as colour. A uniform-opacity overlay
 *     reads as flat paint over the terrain; letting shallow water sit at
 *     ~50% and deep channel approach opaque makes the flood read as water
 *     lying ON a landscape, with the ridges and gullies still visible
 *     underneath the shallow margins. It is also honest: the faintest pixels
 *     are the ones the model is least certain about.
 *   * Anything below the wet threshold is fully transparent, not "very pale
 *     blue". A near-zero-depth tint spread across the whole domain would
 *     imply inundation the solver never produced.
 */

import type {
  DecodedSimulation,
  SimulationPayload,
} from "../types/simulation";

/** Depth is stored as centimetres in a uint16 (backend DEPTH_SCALE). */
export const DEPTH_SCALE = 100;

/** Below this, a cell is dry and draws nothing at all. */
export const WET_THRESHOLD_M = 0.05;

/**
 * Depth over which the shallow margin fades in from fully transparent.
 *
 * A hard alpha cutoff at the wet threshold looks wrong once the grid is
 * upscaled to screen size: the renderer's bilinear filter interpolates
 * between "invisible" and "solid" across a single cell, which reads as
 * stair-stepping and speckle along every shoreline. Fading alpha across a
 * narrow depth band instead gives the margin a soft edge, and does it in
 * depth space, so the softness follows the water rather than the zoom level.
 */
const FEATHER_M = 0.15;

/**
 * Ramp stops as [position 0-1, r, g, b, a].
 *
 * Positions are on a *normalised* depth axis, so the ramp always spans the
 * scene's actual range rather than assuming metres — a 0.5 m sheet flood and
 * a 9 m canyon torrent both use the full range of colour.
 */
const RAMP_STOPS: Array<[number, number, number, number, number]> = [
  [0.0, 0x7f, 0xe9, 0xff, 0.45],   // pale cyan — the shallow margin
  [0.15, 0x3b, 0xa7, 0xff, 0.66],  // Kairos blue
  [0.38, 0x4f, 0x6b, 0xff, 0.8],   // deepening blue
  [0.62, 0x7b, 0x61, 0xff, 0.88],  // indigo
  [0.82, 0xb8, 0x4f, 0xe0, 0.93],  // violet
  [1.0, 0xe8, 0x5c, 0xcf, 0.97],   // magenta — the deepest water
];

/** 256-entry RGBA lookup table, built once and reused for every frame. */
function buildRampLut(): Uint8ClampedArray {
  const lut = new Uint8ClampedArray(256 * 4);
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    let lo = RAMP_STOPS[0];
    let hi = RAMP_STOPS[RAMP_STOPS.length - 1];
    for (let s = 0; s < RAMP_STOPS.length - 1; s++) {
      if (t >= RAMP_STOPS[s][0] && t <= RAMP_STOPS[s + 1][0]) {
        lo = RAMP_STOPS[s];
        hi = RAMP_STOPS[s + 1];
        break;
      }
    }
    const span = hi[0] - lo[0] || 1;
    const f = (t - lo[0]) / span;
    lut[i * 4 + 0] = lo[1] + (hi[1] - lo[1]) * f;
    lut[i * 4 + 1] = lo[2] + (hi[2] - lo[2]) * f;
    lut[i * 4 + 2] = lo[3] + (hi[3] - lo[3]) * f;
    lut[i * 4 + 3] = (lo[4] + (hi[4] - lo[4]) * f) * 255;
  }
  return lut;
}

const RAMP_LUT = buildRampLut();

/**
 * Ramp colour for a normalised depth, as RGBA bytes.
 *
 * Shared with the 3D view so the water mesh's vertex colours and the 2D
 * overlay's pixels come from one ramp — two ramps that drift apart would mean
 * the same depth reads as two different colours depending on the view.
 */
export function rampLookup(t: number): [number, number, number, number] {
  const clamped = t < 0 ? 0 : t > 1 ? 1 : t;
  const i = Math.round(clamped * 255) * 4;
  return [RAMP_LUT[i], RAMP_LUT[i + 1], RAMP_LUT[i + 2], RAMP_LUT[i + 3]];
}

/** CSS gradient for the legend — the same stops the pixels use. */
export function rampCss(): string {
  const stops = RAMP_STOPS.map(
    ([p, r, g, b]) => `rgb(${r},${g},${b}) ${(p * 100).toFixed(0)}%`
  );
  return `linear-gradient(90deg, ${stops.join(", ")})`;
}

/** Colour for one depth (metres) as CSS — used by readouts, not by pixels. */
export function depthColor(depthM: number, peakM: number): string {
  const t = peakM > 0 ? Math.min(Math.max(depthM / peakM, 0), 1) : 0;
  const i = Math.round(t * 255) * 4;
  return `rgb(${RAMP_LUT[i]},${RAMP_LUT[i + 1]},${RAMP_LUT[i + 2]})`;
}

/**
 * Base64 -> bytes at native speed.
 *
 * A 9 MB payload decoded with a per-character `atob` loop costs hundreds of
 * milliseconds on the main thread; routing it through a data URL hands the
 * work to the browser's own decoder instead.
 */
async function base64ToBytes(b64: string): Promise<Uint8Array> {
  try {
    const res = await fetch(`data:application/octet-stream;base64,${b64}`);
    return new Uint8Array(await res.arrayBuffer());
  } catch {
    // Fallback for any environment where data-URL fetch is unavailable.
    const binary = atob(b64);
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
    return out;
  }
}

/** Turn a wire payload into typed arrays ready for rendering. */
export async function decodeSimulation(
  payload: SimulationPayload
): Promise<DecodedSimulation> {
  const { meta } = payload;
  const [demBytes, depthBytes] = await Promise.all([
    base64ToBytes(payload.dem_b64),
    base64ToBytes(payload.depth_b64),
  ]);

  const dem = new Float32Array(
    demBytes.buffer,
    demBytes.byteOffset,
    demBytes.byteLength / 4
  );
  const depths = new Uint16Array(
    depthBytes.buffer,
    depthBytes.byteOffset,
    depthBytes.byteLength / 2
  );

  const expected = meta.ny * meta.nx;
  if (dem.length !== expected) {
    throw new Error(
      `Terrain array is ${dem.length} cells but the payload declares ` +
        `${meta.ny}x${meta.nx} = ${expected}.`
    );
  }
  if (depths.length !== expected * meta.n_frames) {
    throw new Error(
      `Depth array is ${depths.length} cells but the payload declares ` +
        `${meta.n_frames} frames of ${expected}.`
    );
  }

  let peakCm = 0;
  for (let i = 0; i < depths.length; i++) {
    if (depths[i] > peakCm) peakCm = depths[i];
  }

  return {
    meta,
    dem,
    depths,
    ny: meta.ny,
    nx: meta.nx,
    frames: meta.n_frames,
    times: meta.times,
    peakCm,
  };
}

export interface RenderOptions {
  /** Depth (m) mapped to the top of the ramp. Defaults to the scene peak. */
  depthScaleM?: number;
  /** Multiplies the ramp's own alpha. 1 = the ramp as designed. */
  opacity?: number;
}

/**
 * Colourise one frame into an ImageData the size of the grid.
 *
 * Row 0 of the array is north (see backend solver/grid.py), and ImageData row
 * 0 is the top of the image, so the two agree with no flip.
 */
export function renderFrame(
  sim: DecodedSimulation,
  frameIndex: number,
  target: ImageData,
  options: RenderOptions = {}
): ImageData {
  const { ny, nx, depths } = sim;
  const cells = ny * nx;
  const frame = Math.min(Math.max(frameIndex, 0), sim.frames - 1);
  const offset = frame * cells;

  const peakM = options.depthScaleM ?? sim.peakCm / DEPTH_SCALE;
  const peakCm = Math.max(peakM * DEPTH_SCALE, 1);
  const opacity = options.opacity ?? 1;
  const thresholdCm = WET_THRESHOLD_M * DEPTH_SCALE;
  const featherCm = FEATHER_M * DEPTH_SCALE;

  const out = target.data;
  for (let i = 0; i < cells; i++) {
    const cm = depths[offset + i];
    const p = i * 4;
    if (cm < thresholdCm) {
      // Dry: clear the colour channels too, not just alpha. The buffer is
      // reused between frames, and a transparent pixel that still carries the
      // previous frame's colour bleeds that colour into its neighbours when
      // the renderer filters the upscaled texture — non-premultiplied alpha
      // interpolates RGB independently of A, so stale magenta under alpha 0
      // shows up as a fringe along the shoreline.
      out[p] = 0;
      out[p + 1] = 0;
      out[p + 2] = 0;
      out[p + 3] = 0;
      continue;
    }
    let t = cm / peakCm;
    if (t > 1) t = 1;
    const lut = Math.round(t * 255) * 4;
    // Fade the thinnest water in rather than switching it on.
    const edge = Math.min((cm - thresholdCm) / featherCm, 1);
    out[p] = RAMP_LUT[lut];
    out[p + 1] = RAMP_LUT[lut + 1];
    out[p + 2] = RAMP_LUT[lut + 2];
    out[p + 3] = RAMP_LUT[lut + 3] * opacity * edge;
  }
  return target;
}

/**
 * A depth (m) that maps the ramp across the depths that actually cover ground.
 *
 * Two failure modes sit either side of this number, and both were checked
 * against rendered output on real terrain rather than reasoned about:
 *
 *   * Scale to the absolute peak and a handful of outlier channel cells own
 *     the top of the ramp. On the Guadalupe scene the deepest cell is 8.8 m
 *     while the median wet cell is 1.65 m, so effectively the entire flood
 *     renders in one flat blue with no visible depth structure.
 *   * Scale to a typical depth (p97 was tried) and most of the water
 *     saturates at the top of the ramp. The flood comes out magenta and
 *     stops reading as water at all.
 *
 * Taking p99 of the wet depths with headroom lands between the two: the
 * median wet cell falls around a quarter of the way up the ramp (blue), p99
 * around 0.7 (indigo), and only genuinely exceptional depths reach magenta.
 * Verified to hold on both a river valley and a slot canyon.
 *
 * Computed from a histogram rather than a sort — this runs over every cell of
 * every frame. The slider still reaches the true peak; this only picks where
 * it starts.
 */
export function suggestedDepthScaleM(sim: DecodedSimulation, percentile = 0.99): number {
  const peakCm = sim.peakCm;
  if (peakCm <= 0) return 0.25;

  const BINS = 512;
  const hist = new Uint32Array(BINS);
  const thresholdCm = WET_THRESHOLD_M * DEPTH_SCALE;
  let wet = 0;
  for (let i = 0; i < sim.depths.length; i++) {
    const cm = sim.depths[i];
    if (cm < thresholdCm) continue;
    wet++;
    const bin = Math.min(Math.floor((cm / peakCm) * (BINS - 1)), BINS - 1);
    hist[bin]++;
  }
  if (wet === 0) return Math.max(peakCm / DEPTH_SCALE, 0.25);

  // Headroom above the percentile, so p99 lands in the indigo band rather
  // than at the very top of the ramp.
  const HEADROOM = 1.45;
  const target = wet * percentile;
  let cumulative = 0;
  for (let b = 0; b < BINS; b++) {
    cumulative += hist[b];
    if (cumulative >= target) {
      const cm = Math.min(((b + 1) / BINS) * peakCm * HEADROOM, peakCm);
      return Math.max(cm / DEPTH_SCALE, 0.25);
    }
  }
  return Math.max(peakCm / DEPTH_SCALE, 0.25);
}

/** Wet-cell count for one frame — drives the extent readout and sparkline. */
export function wetCells(sim: DecodedSimulation, frameIndex: number): number {
  const cells = sim.ny * sim.nx;
  const offset = Math.min(Math.max(frameIndex, 0), sim.frames - 1) * cells;
  const thresholdCm = WET_THRESHOLD_M * DEPTH_SCALE;
  let count = 0;
  for (let i = 0; i < cells; i++) {
    if (sim.depths[offset + i] >= thresholdCm) count++;
  }
  return count;
}

/** Peak depth (m) in one frame. */
export function framePeakM(sim: DecodedSimulation, frameIndex: number): number {
  const cells = sim.ny * sim.nx;
  const offset = Math.min(Math.max(frameIndex, 0), sim.frames - 1) * cells;
  let peak = 0;
  for (let i = 0; i < cells; i++) {
    if (sim.depths[offset + i] > peak) peak = sim.depths[offset + i];
  }
  return peak / DEPTH_SCALE;
}

/** Flooded area in km² for one frame. */
export function frameAreaKm2(sim: DecodedSimulation, frameIndex: number): number {
  const cellArea = sim.meta.dx * sim.meta.dx;
  return (wetCells(sim, frameIndex) * cellArea) / 1e6;
}

/** "T+1h 23m" — elapsed time from the start of the event. */
export function formatElapsed(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  if (h === 0) return `T+${m}m`;
  return `T+${h}h ${String(m).padStart(2, "0")}m`;
}
