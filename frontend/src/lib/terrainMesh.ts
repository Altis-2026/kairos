import { rampLookup, DEPTH_SCALE, WET_THRESHOLD_M } from "./simulation";
import { burnColour } from "./fire";
import type { DecodedFire, DecodedSimulation } from "../types/simulation";

export interface GridMesh {
  xz: Float32Array;

  indices: Uint32Array;

  uv: Float32Array;

  gridVertexCount: number;

  vertexCount: number;

  gridIndexCount: number;

  indexCount: number;

  perimeter: Uint32Array;

  widthM: number;
  depthM: number;
}

function perimeterIndices(ny: number, nx: number): Uint32Array {
  const ring: number[] = [];
  for (let c = 0; c < nx; c++) ring.push(c);
  for (let r = 1; r < ny; r++) ring.push(r * nx + (nx - 1));
  for (let c = nx - 2; c >= 0; c--) ring.push((ny - 1) * nx + c);
  for (let r = ny - 2; r >= 1; r--) ring.push(r * nx);
  return Uint32Array.from(ring);
}

export function buildGridMesh(ny: number, nx: number, dx: number): GridMesh {
  const gridVertexCount = ny * nx;
  const perimeter = perimeterIndices(ny, nx);

  const vertexCount = gridVertexCount + perimeter.length;

  const xz = new Float32Array(vertexCount * 2);
  const uv = new Float32Array(vertexCount * 2);

  const halfX = ((nx - 1) * dx) / 2;
  const halfZ = ((ny - 1) * dx) / 2;

  for (let r = 0; r < ny; r++) {
    for (let c = 0; c < nx; c++) {
      const i = r * nx + c;
      xz[i * 2] = c * dx - halfX;
      xz[i * 2 + 1] = r * dx - halfZ;
      uv[i * 2] = c / (nx - 1);
      uv[i * 2 + 1] = r / (ny - 1);
    }
  }

  for (let i = 0; i < perimeter.length; i++) {
    const src = perimeter[i];
    const dst = gridVertexCount + i;
    xz[dst * 2] = xz[src * 2];
    xz[dst * 2 + 1] = xz[src * 2 + 1];
    uv[dst * 2] = uv[src * 2];
    uv[dst * 2 + 1] = uv[src * 2 + 1];
  }

  const quads = (ny - 1) * (nx - 1);
  const gridIndexCount = quads * 6;
  const indices = new Uint32Array(gridIndexCount + perimeter.length * 6);
  let k = 0;
  for (let r = 0; r < ny - 1; r++) {
    for (let c = 0; c < nx - 1; c++) {
      const tl = r * nx + c;
      const tr = tl + 1;
      const bl = tl + nx;
      const br = bl + 1;
      indices[k++] = tl;
      indices[k++] = bl;
      indices[k++] = tr;
      indices[k++] = tr;
      indices[k++] = bl;
      indices[k++] = br;
    }
  }

  for (let i = 0; i < perimeter.length; i++) {
    const j = (i + 1) % perimeter.length;
    const top = perimeter[i];
    const nextTop = perimeter[j];
    const bottom = gridVertexCount + i;
    const nextBottom = gridVertexCount + j;
    indices[k++] = top;
    indices[k++] = bottom;
    indices[k++] = nextTop;
    indices[k++] = nextTop;
    indices[k++] = bottom;
    indices[k++] = nextBottom;
  }

  return {
    xz,
    indices,
    uv,
    gridVertexCount,
    vertexCount,
    gridIndexCount,
    indexCount: indices.length,
    perimeter,
    widthM: (nx - 1) * dx,
    depthM: (ny - 1) * dx,
  };
}

export function terrainHeights(
  dem: Float32Array,
  mesh: GridMesh,
  exaggeration: number,
  base: number,
  skirtDrop: number
): Float32Array {
  const y = new Float32Array(mesh.vertexCount);
  for (let i = 0; i < dem.length; i++) y[i] = (dem[i] - base) * exaggeration;
  const drop = skirtDrop * exaggeration;
  for (let i = 0; i < mesh.perimeter.length; i++) {
    y[mesh.gridVertexCount + i] = y[mesh.perimeter[i]] - drop;
  }
  return y;
}

export function skirtFlags(mesh: GridMesh): Float32Array {
  const flags = new Float32Array(mesh.vertexCount);
  flags.fill(1, mesh.gridVertexCount);
  return flags;
}

export function terrainNormals(
  dem: Float32Array,
  mesh: GridMesh,
  ny: number,
  nx: number,
  dx: number,
  exaggeration: number
): Float32Array {
  const out = new Float32Array(mesh.vertexCount * 3);
  for (let r = 0; r < ny; r++) {
    for (let c = 0; c < nx; c++) {
      const i = r * nx + c;
      const left = dem[i - (c > 0 ? 1 : 0)];
      const right = dem[i + (c < nx - 1 ? 1 : 0)];
      const up = dem[i - (r > 0 ? nx : 0)];
      const down = dem[i + (r < ny - 1 ? nx : 0)];
      const spanX = (c > 0 && c < nx - 1 ? 2 : 1) * dx;
      const spanZ = (r > 0 && r < ny - 1 ? 2 : 1) * dx;

      const nxv = -((right - left) * exaggeration) / spanX;
      const nzv = -((down - up) * exaggeration) / spanZ;
      const len = Math.hypot(nxv, 1, nzv) || 1;
      out[i * 3] = nxv / len;
      out[i * 3 + 1] = 1 / len;
      out[i * 3 + 2] = nzv / len;
    }
  }

  for (let i = 0; i < mesh.perimeter.length; i++) {
    const src = mesh.perimeter[i];
    const dst = mesh.gridVertexCount + i;
    const ox = mesh.xz[src * 2];
    const oz = mesh.xz[src * 2 + 1];
    const len = Math.hypot(ox, oz) || 1;
    out[dst * 3] = ox / len;
    out[dst * 3 + 1] = -0.25;
    out[dst * 3 + 2] = oz / len;
  }
  return out;
}

export function dryOffsetFor(demMin: number, demMax: number): number {
  return Math.max(10, (demMax - demMin) * 0.05);
}

export function waterHeights(
  sim: DecodedSimulation,
  frameIndex: number,
  terrainY: Float32Array,
  exaggeration: number,
  dryOffset: number,
  out: Float32Array
): Float32Array {
  const cells = sim.ny * sim.nx;
  const frame = Math.min(Math.max(frameIndex, 0), sim.frames - 1);
  const offset = frame * cells;
  const thresholdCm = WET_THRESHOLD_M * DEPTH_SCALE;
  const buried = dryOffset * exaggeration;

  for (let i = 0; i < cells; i++) {
    const cm = sim.depths[offset + i];
    out[i] = cm < thresholdCm ? terrainY[i] - buried : terrainY[i] + (cm / DEPTH_SCALE) * exaggeration;
  }
  return out;
}

export function waterColors(
  sim: DecodedSimulation,
  frameIndex: number,
  depthScaleM: number,
  out: Uint8Array
): Uint8Array {
  const cells = sim.ny * sim.nx;
  const frame = Math.min(Math.max(frameIndex, 0), sim.frames - 1);
  const offset = frame * cells;
  const thresholdCm = WET_THRESHOLD_M * DEPTH_SCALE;
  const peakCm = Math.max(depthScaleM * DEPTH_SCALE, 1);

  for (let i = 0; i < cells; i++) {
    const cm = sim.depths[offset + i];
    const p = i * 4;
    if (cm < thresholdCm) {
      out[p] = out[p + 1] = out[p + 2] = out[p + 3] = 0;
      continue;
    }
    const [r, g, bl, a] = rampLookup(cm / peakCm);
    out[p] = r;
    out[p + 1] = g;
    out[p + 2] = bl;
    out[p + 3] = a;
  }
  return out;
}

export interface FloodedExtent {
  minRow: number;
  maxRow: number;
  minCol: number;
  maxCol: number;

  meanElevation: number;
  cells: number;
}

export function floodedExtent(sim: DecodedSimulation): FloodedExtent | null {
  const { ny, nx, depths, dem } = sim;
  const cells = ny * nx;
  const thresholdCm = WET_THRESHOLD_M * DEPTH_SCALE;

  let minRow = ny;
  let maxRow = -1;
  let minCol = nx;
  let maxCol = -1;
  let elevationSum = 0;
  let wetCells = 0;

  for (let i = 0; i < cells; i++) {
    let wet = false;
    for (let f = 0; f < sim.frames; f++) {
      if (depths[f * cells + i] >= thresholdCm) {
        wet = true;
        break;
      }
    }
    if (!wet) continue;
    const r = (i / nx) | 0;
    const c = i - r * nx;
    if (r < minRow) minRow = r;
    if (r > maxRow) maxRow = r;
    if (c < minCol) minCol = c;
    if (c > maxCol) maxCol = c;
    elevationSum += dem[i];
    wetCells++;
  }

  if (wetCells === 0) return null;
  return {
    minRow,
    maxRow,
    minCol,
    maxCol,
    meanElevation: elevationSum / wetCells,
    cells: wetCells,
  };
}

export function hillshadeTexture(dem: Float32Array, ny: number, nx: number): ImageData {
  const img = new ImageData(nx, ny);
  const az = (315 * Math.PI) / 180;
  const alt = (42 * Math.PI) / 180;
  const lx = Math.cos(alt) * Math.cos(az);
  const ly = Math.cos(alt) * Math.sin(az);
  const lz = Math.sin(alt);

  let lo = Infinity;
  let hi = -Infinity;
  for (let i = 0; i < dem.length; i++) {
    if (dem[i] < lo) lo = dem[i];
    if (dem[i] > hi) hi = dem[i];
  }
  const span = hi - lo || 1;

  for (let r = 0; r < ny; r++) {
    for (let c = 0; c < nx; c++) {
      const i = r * nx + c;
      const left = dem[i - (c > 0 ? 1 : 0)];
      const right = dem[i + (c < nx - 1 ? 1 : 0)];
      const up = dem[i - (r > 0 ? nx : 0)];
      const down = dem[i + (r < ny - 1 ? nx : 0)];
      const nxv = -(right - left) / 2;
      const nyv = -(down - up) / 2;
      const nzv = 8;
      const len = Math.hypot(nxv, nyv, nzv) || 1;
      const shade = Math.max(0, Math.min(1, (nxv * lx + nyv * ly + nzv * lz) / len));
      const elev = (dem[i] - lo) / span;

      const base = 0.55 + 0.45 * shade;
      const p = i * 4;
      img.data[p] = 255 * base * (0.5 + 0.32 * elev);
      img.data[p + 1] = 255 * base * (0.56 + 0.28 * elev);
      img.data[p + 2] = 255 * base * (0.44 + 0.26 * elev);
      img.data[p + 3] = 255;
    }
  }
  return img;
}

const BURN_LIFT_FRACTION = 0.004;

export function burnHeights(
  fire: DecodedFire,
  minutes: number,
  terrainY: Float32Array,
  exaggeration: number,
  dryOffset: number,
  relief: number,
  out: Float32Array
): Float32Array {
  const cells = fire.ny * fire.nx;
  const buried = dryOffset * exaggeration;
  const lift = Math.max(relief * BURN_LIFT_FRACTION, 0.5) * exaggeration;

  for (let i = 0; i < cells; i++) {
    const t = fire.arrival[i];
    out[i] = t >= fire.unburned || t > minutes ? terrainY[i] - buried : terrainY[i] + lift;
  }
  return out;
}

export function burnColors(
  fire: DecodedFire,
  minutes: number,
  frontMinutes: number,
  out: Uint8Array
): Uint8Array {
  const cells = fire.ny * fire.nx;

  for (let i = 0; i < cells; i++) {
    const t = fire.arrival[i];
    const p = i * 4;
    if (t >= fire.unburned || t > minutes) {
      out[p] = out[p + 1] = out[p + 2] = out[p + 3] = 0;
      continue;
    }
    const age = minutes - t;
    const colour = burnColour(age, frontMinutes)!;
    out[p] = colour[0];
    out[p + 1] = colour[1];
    out[p + 2] = colour[2];

    out[p + 3] = age <= frontMinutes ? 255 : 215;
  }
  return out;
}

export function burnedExtent(fire: DecodedFire): FloodedExtent | null {
  const { ny, nx, arrival, dem, unburned } = fire;

  let minRow = ny;
  let maxRow = -1;
  let minCol = nx;
  let maxCol = -1;
  let sum = 0;
  let count = 0;

  for (let row = 0; row < ny; row++) {
    for (let col = 0; col < nx; col++) {
      const i = row * nx + col;
      if (arrival[i] >= unburned) continue;
      if (row < minRow) minRow = row;
      if (row > maxRow) maxRow = row;
      if (col < minCol) minCol = col;
      if (col > maxCol) maxCol = col;
      sum += dem[i];
      count += 1;
    }
  }

  if (count === 0) return null;
  return {
    minRow,
    maxRow,
    minCol,
    maxCol,
    meanElevation: sum / count,
    cells: count,
  };
}
