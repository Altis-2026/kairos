/**
 * Shared logic for putting an analysis result onto the globe.
 *
 * A single result can render as several stacked layers: any reference/context
 * layers first (drawn underneath), then the detection raster on top, then point
 * features (e.g. detected vessels). Used by both the chat flow and the
 * pin-drop quick-analysis panel so they behave identically.
 */
import { bboxCenterZoom, useMapStore } from "../stores/mapStore";
import { saveCase } from "./cases";
import type { AnalysisResult } from "../types/analysis";

export function applyResultToGlobe(result: AnalysisResult) {
  const map = useMapStore.getState();
  const stamp = Date.now();
  const layerId = `${result.analysis_type}-${stamp}`;

  // Context/reference layers go down first so the detection draws on top.
  for (const ctx of result.context_layers ?? []) {
    map.addRasterLayer({
      id: `${ctx.id}-${stamp}`,
      name: ctx.name,
      tileUrl: ctx.tile_url,
      opacity: 0.55,
      visible: true,
      color: ctx.color,
    });
  }

  map.addRasterLayer({
    id: layerId,
    name: `${result.display_name} · ${result.data_date}`,
    tileUrl: result.tile_url,
    opacity: 0.85,
    visible: true,
    color: "#00BFA8",
  });

  const points = result.stats?.vessel_points as
    | GeoJSON.FeatureCollection
    | undefined;
  if (points?.features?.length) {
    map.addPointLayer({
      id: `${layerId}-pts`,
      name: `${result.display_name} points`,
      data: points,
      color: "#E8A318",
      visible: true,
    });
  }

  // Record it so the research/export tools can act on the latest result
  // regardless of how it was produced.
  map.setLastResult({
    analysisType: result.analysis_type,
    displayName: result.display_name,
    bbox: result.bbox,
    startDate: result.start_date,
    endDate: result.end_date,
    dataDate: result.data_date,
    confidence: result.confidence,
    headlineLabel: result.headline_stat.label,
    headlineValue: result.headline_stat.value,
    headlineUnit: result.headline_stat.unit,
    stats: result.stats,
  });

  // Persist for signed-in users (no-op otherwise) — fire and forget.
  void saveCase(result);

  const { center, zoom } = bboxCenterZoom(result.bbox);
  map.requestFlyTo(center, zoom);
}
