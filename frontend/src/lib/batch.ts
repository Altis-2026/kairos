import { runAnalyze } from "../api/analyze";
import type { BBox } from "../types/map";

export interface BatchInput {
  label: string;
  analysis_type: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
}

export type BatchStatus = "pending" | "running" | "ok" | "no_data" | "error";

export interface BatchRow {
  id: number;
  input: BatchInput;
  status: BatchStatus;
  headlineValue?: number;
  headlineUnit?: string;
  headlineLabel?: string;
  dataDate?: string;
  confidence?: number;
  tileUrl?: string;
  error?: string;
}

function splitCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        cur += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out.map((s) => s.trim());
}

export interface ParseResult {
  inputs: BatchInput[];
  errors: string[];
}

const REQUIRED = [
  "analysis_type",
  "min_lon",
  "min_lat",
  "max_lon",
  "max_lat",
  "start_date",
  "end_date",
];

export function parseBatchCsv(text: string): ParseResult {
  const errors: string[] = [];
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  if (lines.length < 2) {
    return { inputs: [], errors: ["Need a header row plus at least one data row."] };
  }

  const header = splitCsvLine(lines[0]).map((h) => h.toLowerCase());
  const missing = REQUIRED.filter((c) => !header.includes(c));
  if (missing.length) {
    return {
      inputs: [],
      errors: [`Missing required column(s): ${missing.join(", ")}.`],
    };
  }
  const col = (name: string) => header.indexOf(name);

  const inputs: BatchInput[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cells = splitCsvLine(lines[i]);
    const get = (name: string) => cells[col(name)] ?? "";
    const nums = [
      Number(get("min_lon")),
      Number(get("min_lat")),
      Number(get("max_lon")),
      Number(get("max_lat")),
    ];
    if (nums.some((n) => Number.isNaN(n))) {
      errors.push(`Row ${i}: bbox values must be numbers.`);
      continue;
    }
    const analysis_type = get("analysis_type");
    const start_date = get("start_date");
    const end_date = get("end_date");
    if (!analysis_type || !start_date || !end_date) {
      errors.push(`Row ${i}: analysis_type, start_date and end_date are required.`);
      continue;
    }
    const labelIdx = col("label");
    inputs.push({
      label: labelIdx >= 0 && cells[labelIdx] ? cells[labelIdx] : `Site ${i}`,
      analysis_type,
      bbox: [nums[0], nums[1], nums[2], nums[3]] as BBox,
      start_date,
      end_date,
    });
  }
  return { inputs, errors };
}

export async function runBatch(
  rows: BatchRow[],
  onUpdate: (rows: BatchRow[]) => void,
  concurrency = 3
): Promise<void> {
  const snapshot = rows.map((r) => ({ ...r }));
  let cursor = 0;

  async function worker() {
    while (cursor < snapshot.length) {
      const idx = cursor++;
      const row = snapshot[idx];
      row.status = "running";
      onUpdate([...snapshot]);
      try {
        const res = await runAnalyze({
          analysis_type: row.input.analysis_type,
          bbox: row.input.bbox,
          start_date: row.input.start_date,
          end_date: row.input.end_date,
        });
        row.status = "ok";
        row.headlineLabel = res.headline_stat.label;
        row.headlineValue = res.headline_stat.value;
        row.headlineUnit = res.headline_stat.unit;
        row.dataDate = res.data_date;
        row.confidence = res.confidence;
        row.tileUrl = res.tile_url;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Failed";

        row.status = /no .*data|not enough data/i.test(msg) ? "no_data" : "error";
        row.error = msg;
      }
      onUpdate([...snapshot]);
    }
  }

  const workers = Array.from({ length: Math.min(concurrency, snapshot.length) }, () =>
    worker()
  );
  await Promise.all(workers);
}

export function batchResultsToCsv(rows: BatchRow[]): string {
  const header = [
    "label",
    "analysis_type",
    "min_lon",
    "min_lat",
    "max_lon",
    "max_lat",
    "start_date",
    "end_date",
    "status",
    "headline_label",
    "headline_value",
    "headline_unit",
    "data_date",
    "confidence",
    "error",
  ];
  const esc = (v: unknown) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = rows.map((r) =>
    [
      r.input.label,
      r.input.analysis_type,
      r.input.bbox[0],
      r.input.bbox[1],
      r.input.bbox[2],
      r.input.bbox[3],
      r.input.start_date,
      r.input.end_date,
      r.status,
      r.headlineLabel ?? "",
      r.headlineValue ?? "",
      r.headlineUnit ?? "",
      r.dataDate ?? "",
      r.confidence ?? "",
      r.error ?? "",
    ]
      .map(esc)
      .join(",")
  );
  return [header.join(","), ...lines].join("\n");
}

export const BATCH_TEMPLATE = `label,analysis_type,min_lon,min_lat,max_lon,max_lat,start_date,end_date
Dhaka,flood_extent,90.0,23.5,90.6,24.0,2024-07-01,2024-07-31
Sundarbans,deforestation,89.0,21.6,89.6,22.2,2024-01-01,2024-03-31`;
