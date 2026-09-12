/**
 * Hand-rolled orbit camera for the simulation's 3D view.
 *
 * Drag orbits, wheel dollies. Spherical coordinates around a fixed target,
 * which is all this view needs — there is no scene graph, no object picking
 * and no animation system to justify a 3D library.
 *
 * Elevation is clamped short of the poles: at exactly vertical the up vector
 * and the view direction are parallel and the view basis is undefined, which
 * shows up as the scene flipping over as you drag through the top.
 */
import { lookAt, multiply, perspective, type Mat4, type Vec3 } from "./mat4";

/**
 * Lowest angle the camera may drop to, in radians (~7 degrees).
 *
 * Not just a cosmetic limit: the orbit target sits inside the terrain block,
 * so at a near-horizontal angle the eye ends up below the surface and the
 * view fills with the inside of the mesh. Keeping a few degrees of elevation
 * means the camera stays above the landscape at any reasonable zoom.
 */
export const MIN_ELEVATION = 0.12;
export const MAX_ELEVATION = Math.PI / 2 - 0.02;

export interface OrbitState {
  /** Rotation about the vertical axis, radians. */
  azimuth: number;
  /** Angle above the horizon, radians. */
  elevation: number;
  /** Distance from the target. */
  radius: number;
  target: Vec3;
}

export function createOrbit(radius: number, target: Vec3): OrbitState {
  return {
    // A three-quarter view: high enough to read the terrain, low enough that
    // relief and water depth are both legible.
    azimuth: -Math.PI / 4,
    elevation: 0.58,
    radius,
    target,
  };
}

export function clampElevation(elevation: number): number {
  return Math.min(Math.max(elevation, MIN_ELEVATION), MAX_ELEVATION);
}

export function orbitBy(
  state: OrbitState,
  deltaAzimuth: number,
  deltaElevation: number
): OrbitState {
  return {
    ...state,
    azimuth: state.azimuth + deltaAzimuth,
    elevation: clampElevation(state.elevation + deltaElevation),
  };
}

export function dollyBy(
  state: OrbitState,
  factor: number,
  min: number,
  max: number
): OrbitState {
  return {
    ...state,
    radius: Math.min(Math.max(state.radius * factor, min), max),
  };
}

/** World-space camera position implied by the orbit state. */
export function eyePosition(state: OrbitState): Vec3 {
  const { azimuth, elevation, radius, target } = state;
  const horizontal = Math.cos(elevation) * radius;
  return [
    target[0] + horizontal * Math.sin(azimuth),
    target[1] + Math.sin(elevation) * radius,
    target[2] + horizontal * Math.cos(azimuth),
  ];
}

/** Combined projection * view matrix, ready for the GPU. */
export function viewProjection(
  state: OrbitState,
  aspect: number,
  fovY = Math.PI / 4
): Mat4 {
  const eye = eyePosition(state);
  // Near/far scale with distance so precision stays usable whether the camera
  // is skimming the surface or pulled right back off the domain.
  const near = Math.max(state.radius * 0.01, 0.1);
  const far = state.radius * 10 + 1000;
  return multiply(
    perspective(fovY, aspect, near, far),
    lookAt(eye, state.target, [0, 1, 0])
  );
}
