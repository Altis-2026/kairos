import { describe, expect, it } from "vitest";
import { buildGridMesh, dryOffsetFor } from "../lib/terrainMesh";

describe("terrain mesh", () => {
  it("centres the grid on the origin", () => {
    const mesh = buildGridMesh(3, 4, 10);
    expect(mesh.xz[0]).toBeCloseTo(-15);
    expect(mesh.xz[1]).toBeCloseTo(-10);
    const last = (3 * 4 - 1) * 2;
    expect(mesh.xz[last]).toBeCloseTo(15);
    expect(mesh.xz[last + 1]).toBeCloseTo(10);
  });

  it("indexes only vertices that exist", () => {
    const mesh = buildGridMesh(5, 6, 30);
    const vertexCount = mesh.xz.length / 2;
    expect(Math.max(...mesh.indices)).toBeLessThan(vertexCount);
    expect(mesh.indices.length % 3).toBe(0);
  });

  it("keeps the dry offset positive for flat and steep terrain", () => {
    expect(dryOffsetFor(100, 100)).toBeGreaterThan(0);
    expect(dryOffsetFor(0, 2000)).toBeGreaterThan(dryOffsetFor(0, 20));
  });
});
