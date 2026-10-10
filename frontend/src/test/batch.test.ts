import { describe, expect, it } from "vitest";
import { batchResultsToCsv, parseBatchCsv, BATCH_TEMPLATE } from "../lib/batch";

describe("batch CSV", () => {
  it("parses the shipped template without errors", () => {
    const { inputs, errors } = parseBatchCsv(BATCH_TEMPLATE);
    expect(errors).toEqual([]);
    expect(inputs.length).toBeGreaterThan(0);
    for (const row of inputs) expect(row.bbox).toHaveLength(4);
  });

  it("reports missing columns", () => {
    const { inputs, errors } = parseBatchCsv("label,analysis_type\na,flood_extent");
    expect(inputs).toEqual([]);
    expect(errors[0]).toMatch(/Missing required column/);
  });

  it("skips rows with bad numbers and keeps the rest", () => {
    const csv = [
      "label,analysis_type,min_lon,min_lat,max_lon,max_lat,start_date,end_date",
      "good,flood_extent,90,23,91,24,2024-08-01,2024-08-31",
      "bad,flood_extent,x,23,91,24,2024-08-01,2024-08-31",
    ].join("\n");
    const { inputs, errors } = parseBatchCsv(csv);
    expect(inputs.map((r) => r.label)).toEqual(["good"]);
    expect(errors).toHaveLength(1);
  });

  it("writes a header row when exporting", () => {
    expect(batchResultsToCsv([]).split("\n")[0]).toMatch(/label/);
  });
});
