/**
 * Minimal 4x4 matrix maths for the simulation's 3D view.
 *
 * Column-major, the order WebGL's `uniformMatrix4fv` expects, so matrices go
 * straight to the GPU with `transpose = false`.
 *
 * This exists instead of a dependency because the 3D view needs exactly three
 * operations — a perspective projection, a look-at view, and a multiply — and
 * pulling in a matrix library (or three.js) for one feature costs more bundle
 * than the forty lines below. Every function is pure and unit-tested.
 */

export type Mat4 = Float32Array;
export type Vec3 = [number, number, number];

export function identity(): Mat4 {
  const m = new Float32Array(16);
  m[0] = m[5] = m[10] = m[15] = 1;
  return m;
}

/**
 * Right-handed perspective projection mapping view space into clip space.
 *
 * `fovY` is the vertical field of view in radians.
 */
export function perspective(
  fovY: number,
  aspect: number,
  near: number,
  far: number
): Mat4 {
  const f = 1 / Math.tan(fovY / 2);
  const m = new Float32Array(16);
  m[0] = f / aspect;
  m[5] = f;
  m[10] = (far + near) / (near - far);
  m[11] = -1;
  m[14] = (2 * far * near) / (near - far);
  return m;
}

export function subtract(a: Vec3, b: Vec3): Vec3 {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

export function cross(a: Vec3, b: Vec3): Vec3 {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

export function dot(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

export function normalize(v: Vec3): Vec3 {
  const len = Math.hypot(v[0], v[1], v[2]);
  if (len === 0) return [0, 0, 0];
  return [v[0] / len, v[1] / len, v[2] / len];
}

/** Right-handed view matrix looking from `eye` at `target`. */
export function lookAt(eye: Vec3, target: Vec3, up: Vec3): Mat4 {
  // Camera looks down -Z, so the basis' z axis points back toward the eye.
  const z = normalize(subtract(eye, target));
  let x = cross(up, z);
  if (Math.hypot(x[0], x[1], x[2]) < 1e-8) {
    // Up is parallel to the view direction — nudge it so the basis stays
    // well defined instead of collapsing when the camera looks straight down.
    x = cross([0, 0, 1], z);
  }
  x = normalize(x);
  const y = cross(z, x);

  const m = new Float32Array(16);
  m[0] = x[0]; m[4] = x[1]; m[8] = x[2]; m[12] = -dot(x, eye);
  m[1] = y[0]; m[5] = y[1]; m[9] = y[2]; m[13] = -dot(y, eye);
  m[2] = z[0]; m[6] = z[1]; m[10] = z[2]; m[14] = -dot(z, eye);
  m[15] = 1;
  return m;
}

/** `out = a * b`, applying b first. */
export function multiply(a: Mat4, b: Mat4): Mat4 {
  const out = new Float32Array(16);
  for (let c = 0; c < 4; c++) {
    for (let r = 0; r < 4; r++) {
      let sum = 0;
      for (let k = 0; k < 4; k++) sum += a[k * 4 + r] * b[c * 4 + k];
      out[c * 4 + r] = sum;
    }
  }
  return out;
}

/** Transform a point by a matrix, dividing through by w. */
export function transformPoint(m: Mat4, p: Vec3): Vec3 {
  const x = m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12];
  const y = m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13];
  const z = m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14];
  const w = m[3] * p[0] + m[7] * p[1] + m[11] * p[2] + m[15];
  if (w === 0) return [x, y, z];
  return [x / w, y / w, z / w];
}
