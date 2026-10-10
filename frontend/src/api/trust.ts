import { apiFetch } from "./client";
import type { BBox } from "../types/map";

export interface Benchmark {
  id: string;
  analysis_type: string;
  region: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
  reference: string;
  reference_scale_m: number;
}

export interface BenchmarkMetrics {
  kairos_area_km2: number;
  reference_area_km2: number;
  intersection_km2: number;
  union_km2: number;
  precision: number | null;
  recall: number | null;
  iou: number | null;
  f1: number | null;
}

export interface BenchmarkResult {
  benchmark: Benchmark;
  metrics: BenchmarkMetrics;
  kairos_tile_url: string;
  reference_tile_url: string;
  data_date: string | null;
  caveats: string;
}

export interface ConfounderFinding {
  variable: string;
  finding: string;
  concern: "high" | "some" | "low";
}

export interface ConfounderReport {
  analysis_type: string;
  measurements: Record<string, Record<string, number | null>>;
  findings: ConfounderFinding[];
  overall_concern: "high" | "some" | "low";
}

export function listBenchmarks(): Promise<{ benchmarks: Benchmark[] }> {
  return apiFetch<{ benchmarks: Benchmark[] }>("/validation/benchmarks");
}

export function runBenchmark(benchmarkId: string): Promise<BenchmarkResult> {
  return apiFetch<BenchmarkResult>("/validation/run", {
    method: "POST",
    body: JSON.stringify({ benchmark_id: benchmarkId }),
  });
}

export function checkConfounders(
  analysisType: string,
  bbox: BBox,
  startDate: string,
  endDate: string
): Promise<ConfounderReport> {
  return apiFetch<ConfounderReport>("/confounders", {
    method: "POST",
    body: JSON.stringify({
      analysis_type: analysisType,
      bbox,
      start_date: startDate,
      end_date: endDate,
    }),
  });
}
