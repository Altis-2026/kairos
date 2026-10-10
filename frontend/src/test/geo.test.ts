import { describe, expect, it } from "vitest";
import { aoiAreaKm2, bboxToRing, haversineKm, polygonAreaKm2, polygonBBox } from "../lib/geo";

describe("geo", () => {
  it("measures a degree of latitude as about 111 km", () => {
    expect(haversineKm([0, 0], [0, 1])).toBeCloseTo(111.2, 0);
  });

  it("computes the area of a one-degree box at the equator", () => {
    expect(polygonAreaKm2(bboxToRing([0, 0, 1, 1]))).toBeGreaterThan(12200);
    expect(polygonAreaKm2(bboxToRing([0, 0, 1, 1]))).toBeLessThan(12500);
  });

  it("shrinks boxes toward the poles", () => {
    expect(aoiAreaKm2([0, 60, 1, 61], null)).toBeLessThan(aoiAreaKm2([0, 0, 1, 1], null) * 0.55);
  });

  it("wraps a polygon in its bounding box", () => {
    expect(
      polygonBBox([
        [-97.2, 33.1],
        [-96.9, 32.9],
        [-97.0, 33.3],
      ])
    ).toEqual([-97.2, 32.9, -96.9, 33.3]);
  });
});
