import type { DecodedFire, FirePayload } from "../types/simulation";

export const FIRE_FRAMES = 96;

export const FRONT_MINUTES = 12;

const FRONT_RGB: [number, number, number] = [255, 241, 179];
const HOT_RGB: [number, number, number] = [247, 148, 41];
const COOL_RGB: [number, number, number] = [122, 44, 30];
const OLD_RGB: [number, number, number] = [46, 33, 33];

function mix(a: [number, number, number], b: [number, number, number], t: number): [number, number, number] {
  const u = t < 0 ? 0 : t > 1 ? 1 : t;
  return [
    Math.round(a[0] + (b[0] - a[0]) * u),
    Math.round(a[1] + (b[1] - a[1]) * u),
    Math.round(a[2] + (b[2] - a[2]) * u),
  ];
}

export function burnColour(age: number, frontMinutes = FRONT_MINUTES): [number, number, number] | null {
  if (age < 0) return null;
  if (age <= frontMinutes) return mix(FRONT_RGB, HOT_RGB, age / frontMinutes);
  const cooled = (age - frontMinutes) / (frontMinutes * 6);
  if (cooled <= 1) return mix(HOT_RGB, COOL_RGB, cooled);
  return mix(COOL_RGB, OLD_RGB, Math.min((cooled - 1) / 3, 1));
}

export function burnRampCss(): string {
  const stops = [0, 0.2, 0.45, 0.75, 1].map((f) => {
    const c = burnColour(f * FRONT_MINUTES * 12)!;
    return `rgb(${c[0]},${c[1]},${c[2]}) ${(f * 100).toFixed(0)}%`;
  });
  return `linear-gradient(90deg, ${stops.join(", ")})`;
}

function bytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) out[i] = binary.charCodeAt(i);
  return out;
}

export function decodeFire(payload: FirePayload): DecodedFire {
  const { meta } = payload;
  const { ny, nx } = meta;

  const dem = new Float32Array(bytes(payload.dem_b64).buffer, 0, ny * nx);
  const arrival = new Uint16Array(bytes(payload.arrival_b64).buffer, 0, ny * nx);
  const flame = new Uint16Array(bytes(payload.flame_b64).buffer, 0, ny * nx);

  const times = Array.from({ length: FIRE_FRAMES }, (_, i) => (meta.duration_min * i) / (FIRE_FRAMES - 1));

  return {
    kind: "fire",
    meta,
    dem,
    arrival,
    flame,
    ny,
    nx,
    unburned: meta.arrival_unburned,
    durationMin: meta.duration_min,
    frames: FIRE_FRAMES,
    times,
  };
}

export function renderFire(
  fire: DecodedFire,
  minutes: number,
  ctx: CanvasRenderingContext2D,
  frontMinutes = FRONT_MINUTES
): void {
  const { ny, nx, arrival, unburned } = fire;
  const image = ctx.createImageData(nx, ny);
  const data = image.data;

  for (let i = 0; i < ny * nx; i += 1) {
    const t = arrival[i];
    const o = i * 4;
    if (t >= unburned || t > minutes) {
      data[o] = 0;
      data[o + 1] = 0;
      data[o + 2] = 0;
      data[o + 3] = 0;
      continue;
    }
    const colour = burnColour(minutes - t, frontMinutes)!;
    data[o] = colour[0];
    data[o + 1] = colour[1];
    data[o + 2] = colour[2];

    const age = minutes - t;
    data[o + 3] = age <= frontMinutes ? 255 : 205;
  }
  ctx.putImageData(image, 0, 0);
}

export function burnedHectares(fire: DecodedFire, minutes: number): number {
  const { arrival, unburned, meta } = fire;
  let count = 0;
  for (let i = 0; i < arrival.length; i += 1) {
    const t = arrival[i];
    if (t < unburned && t <= minutes) count += 1;
  }
  return (count * meta.dx * meta.dx) / 1e4;
}

export function frontFlameLength(fire: DecodedFire, minutes: number, frontMinutes = FRONT_MINUTES): number {
  const { arrival, flame, unburned, meta } = fire;
  let peak = 0;
  for (let i = 0; i < arrival.length; i += 1) {
    const t = arrival[i];
    if (t >= unburned || t > minutes || minutes - t > frontMinutes) continue;
    if (flame[i] > peak) peak = flame[i];
  }
  return peak / meta.flame_scale;
}
