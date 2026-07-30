import { apiFetch } from "./client";
import type { BBox } from "../types/map";

export type Hazard = "flood" | "wildfire" | "drought" | "subsidence";

export interface TrendTest {
  ols: {
    slope_per_year: number;
    r_squared: number;
    p_value: number;
    n: number;
  };
  mann_kendall: {
    z: number;
    p_value: number;
    trend: string;
    sen_slope_per_year: number;
    n: number;
  };
  summary: string;
}

export interface RiskOutlook {
  hazard: Hazard;
  score: number;
  level: string;
  tile_url: string;
  legend_label: string;
  drivers: string[];
  seasonal: { months: number[]; peak_months: string[] };
  seasonal_label: string | null;
  trend: TrendTest | null;
  trend_label: string | null;
  trend_points: { date: string; value: number }[];
  skill: { hit_rate: number; reference: string; note: string } | null;
  method: string;
  data_years: string;
}

export function runForesight(hazard: Hazard, bbox: BBox): Promise<RiskOutlook> {
  return apiFetch<RiskOutlook>("/foresight", {
    method: "POST",
    body: JSON.stringify({ hazard, bbox }),
  });
}

export interface AskAnswer {
  answer: string;
  source: "ai" | "data";
}

export function askForesight(
  question: string,
  outlook: RiskOutlook,
  placeName: string
): Promise<AskAnswer> {
  return apiFetch<AskAnswer>("/foresight/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      hazard: outlook.hazard,
      place_name: placeName,
      score: outlook.score,
      level: outlook.level,
      drivers: outlook.drivers,
      peak_months: outlook.seasonal.peak_months,
      trend_summary: outlook.trend?.summary ?? null,
      method: outlook.method,
      data_years: outlook.data_years,
      language: navigator.language || null,
    }),
  });
}
