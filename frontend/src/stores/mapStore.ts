import { create } from "zustand";
import type {
  BaseStyle,
  BBox,
  CompareControl,
  DrawMode,
  PointLayer,
  Projection,
  RasterLayer,
  ResultRef,
  TimelineControl,
} from "../types/map";
import { polygonBBox } from "../lib/geo";

interface FlyToTarget {
  center: [number, number];
  zoom: number;
  ts: number;
}

interface MapState {
  coords: { lng: number; lat: number } | null;
  layers: RasterLayer[];
  pointLayers: PointLayer[];
  aoi: BBox | null;
  aoiPolygon: [number, number][] | null;
  drawMode: DrawMode;
  flyTo: FlyToTarget | null;
  baseStyle: BaseStyle;
  projection: Projection;
  quickAnalysisOpen: boolean;
  viewportBbox: BBox | null;

  tutorialOpen: boolean;
  panelRequest: string | null;

  lastResult: ResultRef | null;
  compare: CompareControl | null;
  timeline: TimelineControl | null;
  timelineIndex: number;

  setCoords: (c: { lng: number; lat: number } | null) => void;
  setViewportBbox: (b: BBox) => void;
  addRasterLayer: (layer: RasterLayer) => void;
  addPointLayer: (layer: PointLayer) => void;
  removeLayer: (id: string) => void;
  clearGroup: (group: "compare" | "timeline") => void;
  setLayerOpacity: (id: string, opacity: number) => void;
  toggleLayerVisible: (id: string) => void;
  setLayerVisible: (id: string, visible: boolean) => void;
  clearLayers: () => void;
  setAoi: (bbox: BBox | null) => void;
  setAoiPolygon: (ring: [number, number][]) => void;
  setDrawMode: (mode: DrawMode) => void;
  requestFlyTo: (center: [number, number], zoom: number) => void;
  setBaseStyle: (s: BaseStyle) => void;
  setProjection: (p: Projection) => void;
  toggleProjection: () => void;
  setQuickAnalysisOpen: (open: boolean) => void;
  setTutorialOpen: (open: boolean) => void;
  requestPanel: (panel: string) => void;
  clearPanelRequest: () => void;
  setLastResult: (r: ResultRef) => void;
  setCompare: (c: CompareControl | null) => void;
  setTimeline: (t: TimelineControl | null) => void;
  setTimelineIndex: (i: number) => void;
}

export const useMapStore = create<MapState>((set) => ({
  coords: null,
  layers: [],
  pointLayers: [],
  aoi: null,
  aoiPolygon: null,
  drawMode: null,
  flyTo: null,
  baseStyle: "satellite",
  projection: "globe",
  quickAnalysisOpen: false,
  viewportBbox: null,
  tutorialOpen: false,
  panelRequest: null,
  lastResult: null,
  compare: null,
  timeline: null,
  timelineIndex: 0,

  setCoords: (coords) => set({ coords }),
  setViewportBbox: (viewportBbox) => set({ viewportBbox }),
  addRasterLayer: (layer) =>
    set((s) => ({
      layers: [...s.layers.filter((l) => l.id !== layer.id), layer],
    })),
  addPointLayer: (layer) =>
    set((s) => ({
      pointLayers: [...s.pointLayers.filter((l) => l.id !== layer.id), layer],
    })),
  removeLayer: (id) =>
    set((s) => ({
      layers: s.layers.filter((l) => l.id !== id),
      pointLayers: s.pointLayers.filter((l) => l.id !== id),
    })),
  clearGroup: (group) =>
    set((s) => ({ layers: s.layers.filter((l) => l.group !== group) })),
  setLayerOpacity: (id, opacity) =>
    set((s) => ({
      layers: s.layers.map((l) => (l.id === id ? { ...l, opacity } : l)),
    })),
  toggleLayerVisible: (id) =>
    set((s) => ({
      layers: s.layers.map((l) =>
        l.id === id ? { ...l, visible: !l.visible } : l
      ),
      pointLayers: s.pointLayers.map((l) =>
        l.id === id ? { ...l, visible: !l.visible } : l
      ),
    })),
  setLayerVisible: (id, visible) =>
    set((s) => ({
      layers: s.layers.map((l) => (l.id === id ? { ...l, visible } : l)),
      pointLayers: s.pointLayers.map((l) =>
        l.id === id ? { ...l, visible } : l
      ),
    })),
  clearLayers: () => set({ layers: [], pointLayers: [] }),
  setAoi: (aoi) => set({ aoi, aoiPolygon: null }),
  setAoiPolygon: (ring) => set({ aoiPolygon: ring, aoi: polygonBBox(ring) }),
  setDrawMode: (drawMode) => set({ drawMode }),
  requestFlyTo: (center, zoom) =>
    set({ flyTo: { center, zoom, ts: Date.now() } }),
  setBaseStyle: (baseStyle) => set({ baseStyle }),
  setProjection: (projection) => set({ projection }),
  toggleProjection: () =>
    set((s) => ({
      projection: s.projection === "globe" ? "mercator" : "globe",
    })),
  setQuickAnalysisOpen: (quickAnalysisOpen) => set({ quickAnalysisOpen }),
  setTutorialOpen: (tutorialOpen) => set({ tutorialOpen }),
  requestPanel: (panelRequest) => set({ panelRequest }),
  clearPanelRequest: () => set({ panelRequest: null }),

  setLastResult: (lastResult) =>
    set((s) => ({
      lastResult,
      layers: s.layers.filter(
        (l) =>
          l.group !== "compare" &&
          l.group !== "timeline" &&
          l.id !== "research-backscatter" &&
          l.id !== "research-optical"
      ),
      compare: null,
      timeline: null,
      timelineIndex: 0,
    })),
  setCompare: (compare) => set({ compare }),
  setTimeline: (timeline) => set({ timeline }),
  setTimelineIndex: (timelineIndex) => set({ timelineIndex }),
}));

export function bboxCenterZoom(bbox: BBox): { center: [number, number]; zoom: number } {
  const [minLon, minLat, maxLon, maxLat] = bbox;
  const center: [number, number] = [
    (minLon + maxLon) / 2,
    (minLat + maxLat) / 2,
  ];
  const span = Math.max(maxLon - minLon, maxLat - minLat);
  const zoom = span > 8 ? 4.5 : span > 4 ? 5.5 : span > 2 ? 6.5 : span > 1 ? 7.5 : 8.5;
  return { center, zoom };
}
