import { fetchGeoTIFF, fetchReport } from "../api/exports";
import type { BBox } from "../types/map";

export interface ExportSource {
  analysis_type: string;
  display_name: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
  data_date: string;
  confidence: number;
  headline_label: string;
  headline_value: number;
  headline_unit: string;
  stats?: Record<string, unknown>;
}

function triggerDownload(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadGeoTIFF(src: ExportSource): Promise<void> {
  const res = await fetchGeoTIFF({
    analysis_type: src.analysis_type,
    bbox: src.bbox,
    start_date: src.start_date,
    end_date: src.end_date,
  });
  window.open(res.download_url, "_blank", "noopener");
}

export async function downloadReport(src: ExportSource): Promise<void> {
  const res = await fetchReport({
    analysis_type: src.analysis_type,
    display_name: src.display_name,
    bbox: src.bbox,
    start_date: src.start_date,
    end_date: src.end_date,
    data_date: src.data_date,
    confidence: src.confidence,
    headline_label: src.headline_label,
    headline_value: src.headline_value,
    headline_unit: src.headline_unit,
    stats: src.stats,
  });
  triggerDownload(res.filename, res.markdown, "text/markdown");
}
