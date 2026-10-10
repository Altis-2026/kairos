import { lookAt, multiply, perspective, type Mat4, type Vec3 } from "./mat4";

export const MIN_ELEVATION = 0.12;
export const MAX_ELEVATION = Math.PI / 2 - 0.02;

export interface OrbitState {
  azimuth: number;

  elevation: number;

  radius: number;
  target: Vec3;
}

export function createOrbit(radius: number, target: Vec3): OrbitState {
  return {
    azimuth: -Math.PI / 4,
    elevation: 0.58,
    radius,
    target,
  };
}

export function clampElevation(elevation: number): number {
  return Math.min(Math.max(elevation, MIN_ELEVATION), MAX_ELEVATION);
}

export function orbitBy(state: OrbitState, deltaAzimuth: number, deltaElevation: number): OrbitState {
  return {
    ...state,
    azimuth: state.azimuth + deltaAzimuth,
    elevation: clampElevation(state.elevation + deltaElevation),
  };
}

export function dollyBy(state: OrbitState, factor: number, min: number, max: number): OrbitState {
  return {
    ...state,
    radius: Math.min(Math.max(state.radius * factor, min), max),
  };
}

export function eyePosition(state: OrbitState): Vec3 {
  const { azimuth, elevation, radius, target } = state;
  const horizontal = Math.cos(elevation) * radius;
  return [
    target[0] + horizontal * Math.sin(azimuth),
    target[1] + Math.sin(elevation) * radius,
    target[2] + horizontal * Math.cos(azimuth),
  ];
}

export function viewProjection(state: OrbitState, aspect: number, fovY = Math.PI / 4): Mat4 {
  const eye = eyePosition(state);

  const near = Math.max(state.radius * 0.01, 0.1);
  const far = state.radius * 10 + 1000;
  return multiply(perspective(fovY, aspect, near, far), lookAt(eye, state.target, [0, 1, 0]));
}
