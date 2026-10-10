import type { DecodedSimulation, SimulationPayload } from "../types/simulation";

export const DEPTH_SCALE = 100;

export const WET_THRESHOLD_M = 0.05;

const FEATHER_M = 0.15;

const RAMP_STOPS: Array<[number, number, number, number, number]> = [
  [0.0, 0x7f, 0xe9, 0xff, 0.45],
  [0.15, 0x3b, 0xa7, 0xff, 0.66],
  [0.38, 0x4f, 0x6b, 0xff, 0.8],
  [0.62, 0x7b, 0x61, 0xff, 0.88],
  [0.82, 0xb8, 0x4f, 0xe0, 0.93],
  [1.0, 0xe8, 0x5c, 0xcf, 0.97],
];

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

export function rampLookup(t: number): [number, number, number, number] {
  const clamped = t < 0 ? 0 : t > 1 ? 1 : t;
  const i = Math.round(clamped * 255) * 4;
  return [RAMP_LUT[i], RAMP_LUT[i + 1], RAMP_LUT[i + 2], RAMP_LUT[i + 3]];
}

export function rampCss(): string {
  const stops = RAMP_STOPS.map(([p, r, g, b]) => `rgb(${r},${g},${b}) ${(p * 100).toFixed(0)}%`);
  return `linear-gradient(90deg, ${stops.join(", ")})`;
}

export function depthColor(depthM: number, peakM: number): string {
  const t = peakM > 0 ? Math.min(Math.max(depthM / peakM, 0), 1) : 0;
  const i = Math.round(t * 255) * 4;
  return `rgb(${RAMP_LUT[i]},${RAMP_LUT[i + 1]},${RAMP_LUT[i + 2]})`;
}

async function base64ToBytes(b64: string): Promise<Uint8Array> {
  try {
    const res = await fetch(`data:application/octet-stream;base64,${b64}`);
    return new Uint8Array(await res.arrayBuffer());
  } catch {
    const binary = atob(b64);
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
    return out;
  }
}

export async function decodeSimulation(payload: SimulationPayload): Promise<DecodedSimulation> {
  const { meta } = payload;
  const [demBytes, depthBytes] = await Promise.all([
    base64ToBytes(payload.dem_b64),
    base64ToBytes(payload.depth_b64),
  ]);

  const dem = new Float32Array(demBytes.buffer, demBytes.byteOffset, demBytes.byteLength / 4);
  const depths = new Uint16Array(depthBytes.buffer, depthBytes.byteOffset, depthBytes.byteLength / 2);

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
  depthScaleM?: number;

  opacity?: number;
}

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
      out[p] = 0;
      out[p + 1] = 0;
      out[p + 2] = 0;
      out[p + 3] = 0;
      continue;
    }
    let t = cm / peakCm;
    if (t > 1) t = 1;
    const lut = Math.round(t * 255) * 4;

    const edge = Math.min((cm - thresholdCm) / featherCm, 1);
    out[p] = RAMP_LUT[lut];
    out[p + 1] = RAMP_LUT[lut + 1];
    out[p + 2] = RAMP_LUT[lut + 2];
    out[p + 3] = RAMP_LUT[lut + 3] * opacity * edge;
  }
  return target;
}

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

export function framePeakM(sim: DecodedSimulation, frameIndex: number): number {
  const cells = sim.ny * sim.nx;
  const offset = Math.min(Math.max(frameIndex, 0), sim.frames - 1) * cells;
  let peak = 0;
  for (let i = 0; i < cells; i++) {
    if (sim.depths[offset + i] > peak) peak = sim.depths[offset + i];
  }
  return peak / DEPTH_SCALE;
}

export function frameAreaKm2(sim: DecodedSimulation, frameIndex: number): number {
  const cellArea = sim.meta.dx * sim.meta.dx;
  return (wetCells(sim, frameIndex) * cellArea) / 1e6;
}

export function formatElapsed(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  if (h === 0) return `T+${m}m`;
  return `T+${h}h ${String(m).padStart(2, "0")}m`;
}
