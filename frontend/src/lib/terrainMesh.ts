/**
 * Build the terrain and water meshes for the simulation's 3D view.
 *
 * Both meshes share one grid — the solver's own — so they need exactly one
 * static index buffer between them and one static XZ buffer. Only the water's
 * per-vertex height and colour change from frame to frame, which is what
 * keeps playback cheap.
 *
 * Occlusion without a custom shader
 * ---------------------------------
 * The hard part of drawing a flood over terrain is hiding the water that
 * should be behind a ridge as the camera orbits. Rather than rebuilding the
 * water surface's triangles every frame to cover only wet cells, every vertex
 * of the full-grid water mesh is placed one of two ways:
 *
 *   wet  ->  y = ground + depth        (the real water surface)
 *   dry  ->  y = ground - dryOffset    (buried under the terrain)
 *
 * Ordinary depth testing then does the work: buried vertices are behind the
 * terrain from every angle, so they are never drawn, and a triangle that
 * straddles the shoreline gets clipped per-fragment exactly where the water
 * surface passes through the ground. One static index buffer, correct
 * occlusion from any camera position, and no shader tricks.
 */
import { rampLookup, DEPTH_SCALE, WET_THRESHOLD_M } from "./simulation";
import { burnColour } from "./fire";
import type { DecodedFire, DecodedSimulation } from "../types/simulation";

export interface GridMesh {
  /** 2 floats per vertex: world X and Z, centred on the origin. */
  xz: Float32Array;
  /**
   * Triangle indices, grid triangles FIRST and then the skirt's.
   *
   * The two meshes share this buffer but draw different amounts of it: the
   * water draws `gridIndexCount` (the surface only) and the terrain draws
   * `indexCount` (surface plus skirt), so the water never gets painted down
   * the sides of the block.
   */
  indices: Uint32Array;
  /** 2 floats per vertex, for draping a basemap image over the terrain. */
  uv: Float32Array;
  /** Vertices in the surface grid: ny * nx. The water only ever uses these. */
  gridVertexCount: number;
  /** Surface grid plus the skirt ring. */
  vertexCount: number;
  /** Indices covering the surface grid alone. */
  gridIndexCount: number;
  /** All indices, surface plus skirt. */
  indexCount: number;
  /** Grid indices of the perimeter, in order, paired with the skirt ring. */
  perimeter: Uint32Array;
  /** Domain size in metres, for framing the camera. */
  widthM: number;
  depthM: number;
}

/**
 * Grid indices around the domain border, walked as a closed loop.
 *
 * Top row west to east, then east column, then bottom row back, then the west
 * column — corners included exactly once so consecutive pairs are genuinely
 * adjacent all the way round.
 */
function perimeterIndices(ny: number, nx: number): Uint32Array {
  const ring: number[] = [];
  for (let c = 0; c < nx; c++) ring.push(c);
  for (let r = 1; r < ny; r++) ring.push(r * nx + (nx - 1));
  for (let c = nx - 2; c >= 0; c--) ring.push((ny - 1) * nx + c);
  for (let r = ny - 2; r >= 1; r--) ring.push(r * nx);
  return Uint32Array.from(ring);
}

/**
 * Static geometry for an (ny, nx) grid of cells `dx` metres apart.
 *
 * Row 0 is north (see backend solver/grid.py), and rows run toward +Z, so
 * north is at negative Z and a camera on +Z looks northward.
 */
export function buildGridMesh(ny: number, nx: number, dx: number): GridMesh {
  const gridVertexCount = ny * nx;
  const perimeter = perimeterIndices(ny, nx);
  // One skirt vertex hanging below each perimeter vertex, so the terrain is a
  // solid block rather than a floating sheet. Without it, water buried under
  // the surface at the domain edge has nothing behind it to be hidden by, and
  // shows as a comb of triangles hanging past the boundary.
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

  // Skirt vertices sit directly below their perimeter vertex.
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
      indices[k++] = tl; indices[k++] = bl; indices[k++] = tr;
      indices[k++] = tr; indices[k++] = bl; indices[k++] = br;
    }
  }

  for (let i = 0; i < perimeter.length; i++) {
    const j = (i + 1) % perimeter.length;
    const top = perimeter[i];
    const nextTop = perimeter[j];
    const bottom = gridVertexCount + i;
    const nextBottom = gridVertexCount + j;
    indices[k++] = top; indices[k++] = bottom; indices[k++] = nextTop;
    indices[k++] = nextTop; indices[k++] = bottom; indices[k++] = nextBottom;
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

/**
 * Terrain vertex heights, vertically exaggerated, including the skirt.
 *
 * Each skirt vertex hangs a fixed distance below *its own* perimeter vertex,
 * so the rim follows the terrain profile. Dropping them all to one global
 * floor instead builds a wall as tall as the boundary relief — on a canyon
 * that is a plinth taller than the landscape, textured with a smear of the
 * basemap, and it dominates the view. The rim only has to reach past the
 * buried water at the edge, which is a constant offset.
 */
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

/**
 * 0 for surface vertices, 1 for the skirt.
 *
 * Lets the shader paint the cut edge a flat colour rather than smearing the
 * basemap down it — skirt vertices inherit their perimeter vertex's UV, so a
 * textured rim streaks.
 */
export function skirtFlags(mesh: GridMesh): Float32Array {
  const flags = new Float32Array(mesh.vertexCount);
  flags.fill(1, mesh.gridVertexCount);
  return flags;
}

/**
 * Per-vertex surface normals for the exaggerated terrain.
 *
 * Computed from the exaggerated surface rather than the raw DEM, so the
 * lighting matches the shape actually on screen — normals from the true
 * elevations would light a landscape flatter than the one being drawn.
 * Central differences, with the domain edges falling back to one-sided.
 */
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

      // Surface tangents are (spanX, dY, 0) and (0, dZ, spanZ); their cross
      // product gives the normal, which simplifies to this.
      const nxv = -((right - left) * exaggeration) / spanX;
      const nzv = -((down - up) * exaggeration) / spanZ;
      const len = Math.hypot(nxv, 1, nzv) || 1;
      out[i * 3] = nxv / len;
      out[i * 3 + 1] = 1 / len;
      out[i * 3 + 2] = nzv / len;
    }
  }

  // Skirt normals point outward and slightly down, so the sides of the block
  // read as walls rather than as more ground.
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

/**
 * How far a dry vertex is pushed below the ground, in metres of real
 * elevation. It has to exceed the elevation change across one cell, or on a
 * steep slope a dry vertex can still sit above its downhill neighbour's
 * terrain and show a sliver of water where there is none.
 */
export function dryOffsetFor(demMin: number, demMax: number): number {
  return Math.max(10, (demMax - demMin) * 0.05);
}

/**
 * Water surface heights for one frame, with dry vertices buried.
 *
 * Writes into `out` so playback reuses one buffer instead of allocating a
 * few hundred kilobytes per frame.
 */
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
    out[i] =
      cm < thresholdCm
        ? terrainY[i] - buried
        : terrainY[i] + (cm / DEPTH_SCALE) * exaggeration;
  }
  return out;
}

/**
 * Per-vertex water colour for one frame, RGBA bytes.
 *
 * Dry vertices get zero alpha as well as being buried — belt and braces, so a
 * dry vertex that does poke through on extreme terrain contributes nothing
 * visible rather than a stray coloured spike.
 */
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
  /** Mean ground elevation under the flood, in metres. */
  meanElevation: number;
  cells: number;
}

/**
 * Bounding box of every cell that is wet at any point in the run.
 *
 * Used to frame the camera. Framing on the whole domain is honest but
 * undersells the result: a river flood is genuinely a thin thread, so on a
 * real AOI it covers a few percent of the grid (4% on the Guadalupe scene,
 * 1.5% in the canyon) and opening the view means hunting for the water.
 * Fitting to the ever-wet extent instead puts the flood in the frame while
 * still showing the terrain it is running through.
 *
 * The union across all frames rather than the peak frame, so the camera does
 * not have to move as the flood grows and drains.
 *
 * Returns null when nothing ever gets wet — callers fall back to the domain.
 */
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
    minRow, maxRow, minCol, maxCol,
    meanElevation: elevationSum / wetCells,
    cells: wetCells,
  };
}

/**
 * A shaded-relief image of the terrain, used as the basemap when satellite
 * imagery is unavailable or switched off.
 *
 * Lambertian shading from the north-west at 42 degrees — the convention
 * topographic maps use, because it is the direction people read as raised
 * rather than sunken.
 */
export function hillshadeTexture(
  dem: Float32Array,
  ny: number,
  nx: number
): ImageData {
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
      // Kept light: this is a base colour that the 3D view lights again, so
      // baking in deep shadow here would double-darken the terrain.
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

// ---------------------------------------------------------------------------
// Wildfire
// ---------------------------------------------------------------------------

/**
 * How far above the ground the burn surface floats, as a fraction of relief.
 *
 * A fire has no depth, so unlike water there is no physical height to use.
 * It still cannot sit exactly on the terrain: coincident surfaces z-fight,
 * producing a shimmering speckle that reads as a rendering fault. This lifts
 * it by a hair — enough to win the depth test everywhere, small enough that
 * the burn still looks painted onto the ground rather than hovering over it.
 */
const BURN_LIFT_FRACTION = 0.004;

/**
 * Burn surface heights at minute `minutes`, with unburned vertices buried.
 *
 * Deliberately the same shape as `waterHeights`, and for the same reason: the
 * 3D viewer's occlusion trick is that unburned geometry is pushed below the
 * terrain so ordinary depth testing hides it. Fire reuses that whole pipeline
 * rather than duplicating it — from the renderer's point of view a burn and a
 * flood are both a coloured surface draped over the same mesh.
 */
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
    out[i] =
      t >= fire.unburned || t > minutes
        ? terrainY[i] - buried
        : terrainY[i] + lift;
  }
  return out;
}

/**
 * Per-vertex burn colour at minute `minutes`, RGBA bytes.
 *
 * Unburned vertices get zero alpha as well as being buried, so a vertex that
 * does poke through on extreme terrain contributes nothing visible.
 */
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
    // The live front is opaque; older burn is translucent so the terrain it
    // ran over still reads through it.
    out[p + 3] = age <= frontMinutes ? 255 : 215;
  }
  return out;
}

/**
 * Bounding box of everything that burns at any point in the run.
 *
 * The fire counterpart of `floodedExtent`, used for the same reason: framing
 * the whole domain puts the burn in a corner of the view.
 */
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
