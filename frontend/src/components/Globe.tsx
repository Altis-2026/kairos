import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useMapStore } from "../stores/mapStore";
import { useSimulationStore } from "../stores/simulationStore";
import { useChatStore } from "../stores/chatStore";
import { renderFrame } from "../lib/simulation";
import { renderFire } from "../lib/fire";
import { escapeHtml, safeHttpUrl } from "../lib/html";
import type { BBox } from "../types/map";

const TOKEN = (import.meta.env.VITE_MAPBOX_TOKEN as string) || "";
mapboxgl.accessToken = TOKEN;

const STYLES = {
  satellite: "mapbox://styles/mapbox/satellite-streets-v12",
  dark: "mapbox://styles/mapbox/dark-v11",
  terrain: "mapbox://styles/mapbox/outdoors-v12",
};

const DEM_SOURCE = "kairos-dem";
const SIM_SOURCE = "kairos-sim-src";
const SIM_LAYER = "kairos-sim-lyr";
const AOI_SOURCE = "kairos-aoi";
const AOI_FILL = "kairos-aoi-fill";
const AOI_LINE = "kairos-aoi-line";
const DRAFT_SOURCE = "kairos-aoi-draft";
const DRAFT_FILL = "kairos-aoi-draft-fill";
const DRAFT_LINE = "kairos-aoi-draft-line";
const DRAFT_POINTS = "kairos-aoi-draft-points";
const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

type Corners = [[number, number], [number, number], [number, number], [number, number]];

function bboxCorners([minLon, minLat, maxLon, maxLat]: number[]): Corners {
  return [
    [minLon, maxLat],
    [maxLon, maxLat],
    [maxLon, minLat],
    [minLon, minLat],
  ];
}

function aoiToFeature(bbox: BBox, ring: [number, number][] | null): GeoJSON.Feature {
  const coords = ring
    ? [...ring, ring[0]]
    : [
        [bbox[0], bbox[1]],
        [bbox[2], bbox[1]],
        [bbox[2], bbox[3]],
        [bbox[0], bbox[3]],
        [bbox[0], bbox[1]],
      ];
  return { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [coords] } };
}

function applyAtmosphere(map: mapboxgl.Map) {
  map.setFog({
    color: "rgba(11, 18, 14, 0.9)",
    "high-color": "rgba(0, 191, 168, 0.12)",
    "horizon-blend": 0.04,
    "space-color": "#070d0a",
    "star-intensity": 0.35,
  });
}

function syncTerrain(map: mapboxgl.Map) {
  const style = useMapStore.getState().baseStyle;
  const { sim, fire, showTerrain } = useSimulationStore.getState();
  const wantTerrain = style === "terrain" || ((sim !== null || fire !== null) && showTerrain);
  if (wantTerrain) {
    if (!map.getSource(DEM_SOURCE)) {
      map.addSource(DEM_SOURCE, {
        type: "raster-dem",
        url: "mapbox://mapbox.mapbox-terrain-dem-v1",
        tileSize: 512,
        maxzoom: 14,
      });
    }
    map.setTerrain({ source: DEM_SOURCE, exaggeration: 1.4 });
  } else {
    map.setTerrain(null);
  }
}

function ensureGeoJson(map: mapboxgl.Map, id: string) {
  if (!map.getSource(id)) map.addSource(id, { type: "geojson", data: EMPTY });
}

function ensureAoiLayers(map: mapboxgl.Map) {
  ensureGeoJson(map, AOI_SOURCE);
  ensureGeoJson(map, DRAFT_SOURCE);
  const layers: mapboxgl.AnyLayer[] = [
    {
      id: AOI_FILL,
      type: "fill",
      source: AOI_SOURCE,
      paint: { "fill-color": "#E8A318", "fill-opacity": 0.08 },
    },
    {
      id: AOI_LINE,
      type: "line",
      source: AOI_SOURCE,
      paint: { "line-color": "#E8A318", "line-width": 1.5, "line-dasharray": [2, 1.5] },
    },
    {
      id: DRAFT_FILL,
      type: "fill",
      source: DRAFT_SOURCE,
      filter: ["==", "$type", "Polygon"],
      paint: { "fill-color": "#E8A318", "fill-opacity": 0.06 },
    },
    {
      id: DRAFT_LINE,
      type: "line",
      source: DRAFT_SOURCE,
      filter: ["==", "$type", "LineString"],
      paint: { "line-color": "#E8A318", "line-width": 1.5, "line-dasharray": [1.5, 1.5] },
    },
    {
      id: DRAFT_POINTS,
      type: "circle",
      source: DRAFT_SOURCE,
      filter: ["==", "$type", "Point"],
      paint: {
        "circle-radius": 4,
        "circle-color": "#E8A318",
        "circle-stroke-width": 1.5,
        "circle-stroke-color": "#0B120E",
      },
    },
  ];
  for (const layer of layers) if (!map.getLayer(layer.id)) map.addLayer(layer);
}

function removeStale(map: mapboxgl.Map, layerPrefix: string, sourcePrefix: string, wanted: Set<string>) {
  for (const l of map.getStyle()?.layers ?? []) {
    if (l.id.startsWith(layerPrefix) && !wanted.has(l.id)) {
      map.removeLayer(l.id);
      const srcId = sourcePrefix + l.id.slice(layerPrefix.length);
      if (map.getSource(srcId)) map.removeSource(srcId);
    }
  }
}

function syncRasterLayers(map: mapboxgl.Map) {
  const current = useMapStore.getState().layers;
  for (const layer of current) {
    const srcId = `kairos-src-${layer.id}`;
    const lyrId = `kairos-lyr-${layer.id}`;
    if (!map.getSource(srcId))
      map.addSource(srcId, { type: "raster", tiles: [layer.tileUrl], tileSize: 256 });
    if (!map.getLayer(lyrId)) map.addLayer({ id: lyrId, type: "raster", source: srcId }, AOI_FILL);
    map.setPaintProperty(lyrId, "raster-opacity", layer.visible ? layer.opacity : 0);
  }
  removeStale(map, "kairos-lyr-", "kairos-src-", new Set(current.map((l) => `kairos-lyr-${l.id}`)));
}

function syncImageLayers(map: mapboxgl.Map) {
  const current = useMapStore.getState().imageLayers;
  for (const layer of current) {
    const srcId = `kairos-img-src-${layer.id}`;
    const lyrId = `kairos-img-lyr-${layer.id}`;
    const coordinates = bboxCorners(layer.bbox);
    const existing = map.getSource(srcId) as mapboxgl.ImageSource | undefined;
    if (!existing) map.addSource(srcId, { type: "image", url: layer.url, coordinates });
    else existing.updateImage({ url: layer.url, coordinates });
    if (!map.getLayer(lyrId)) map.addLayer({ id: lyrId, type: "raster", source: srcId }, AOI_FILL);
    map.setPaintProperty(lyrId, "raster-opacity", layer.visible ? layer.opacity : 0);
    map.setPaintProperty(lyrId, "raster-fade-duration", 0);
  }
  removeStale(
    map,
    "kairos-img-lyr-",
    "kairos-img-src-",
    new Set(current.map((l) => `kairos-img-lyr-${l.id}`))
  );
}

function syncPointLayers(map: mapboxgl.Map) {
  const current = useMapStore.getState().pointLayers;
  for (const layer of current) {
    const srcId = `kairos-pts-src-${layer.id}`;
    const lyrId = `kairos-pts-lyr-${layer.id}`;
    if (!map.getSource(srcId)) map.addSource(srcId, { type: "geojson", data: layer.data });
    if (!map.getLayer(lyrId)) {
      map.addLayer({
        id: lyrId,
        type: "circle",
        source: srcId,
        paint: {
          "circle-radius": ["case", ["has", "title"], 6, 4],
          "circle-color": ["coalesce", ["get", "color"], layer.color],
          "circle-stroke-width": 1,
          "circle-stroke-color": "#0B120E",
        },
      });
    }
    map.setLayoutProperty(lyrId, "visibility", layer.visible ? "visible" : "none");
  }
  removeStale(
    map,
    "kairos-pts-lyr-",
    "kairos-pts-src-",
    new Set(current.map((l) => `kairos-pts-lyr-${l.id}`))
  );
}

function syncAoi(map: mapboxgl.Map) {
  ensureAoiLayers(map);
  const { aoi, aoiPolygon } = useMapStore.getState();
  const source = map.getSource(AOI_SOURCE) as mapboxgl.GeoJSONSource | undefined;
  source?.setData(aoi ? { type: "FeatureCollection", features: [aoiToFeature(aoi, aoiPolygon)] } : EMPTY);
}

function withStyle(map: mapboxgl.Map | null, run: (m: mapboxgl.Map) => void) {
  if (!map) return;
  try {
    run(map);
  } catch {
    map.once("idle", () => {
      try {
        run(map);
      } catch {
        map.once("style.load", () => run(map));
      }
    });
  }
}

export default function Globe() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const spinningRef = useRef(true);
  const drawingRef = useRef<{ start: [number, number] } | null>(null);
  const simCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const simImageRef = useRef<ImageData | null>(null);

  const layers = useMapStore((s) => s.layers);
  const pointLayers = useMapStore((s) => s.pointLayers);
  const imageLayers = useMapStore((s) => s.imageLayers);
  const aoi = useMapStore((s) => s.aoi);
  const aoiPolygon = useMapStore((s) => s.aoiPolygon);
  const drawMode = useMapStore((s) => s.drawMode);
  const flyTo = useMapStore((s) => s.flyTo);
  const baseStyle = useMapStore((s) => s.baseStyle);
  const projection = useMapStore((s) => s.projection);
  const chatLoading = useChatStore((s) => s.loading);

  const sim = useSimulationStore((s) => s.sim);
  const fire = useSimulationStore((s) => s.fire);
  const simFrame = useSimulationStore((s) => s.frame);
  const simFrontMinutes = useSimulationStore((s) => s.frontMinutes);
  const simOpacity = useSimulationStore((s) => s.opacity);
  const simDepthScale = useSimulationStore((s) => s.depthScaleM);
  const simShowFlood = useSimulationStore((s) => s.showFlood);
  const simShowTerrain = useSimulationStore((s) => s.showTerrain);

  function syncSimulation(map: mapboxgl.Map) {
    const state = useSimulationStore.getState();
    const current = state.sim ?? state.fire;
    if (!current) {
      if (map.getLayer(SIM_LAYER)) map.removeLayer(SIM_LAYER);
      if (map.getSource(SIM_SOURCE)) map.removeSource(SIM_SOURCE);
      simCanvasRef.current = null;
      simImageRef.current = null;
      return;
    }

    const { nx, ny } = current;
    let canvas = simCanvasRef.current;
    if (!canvas || canvas.width !== nx || canvas.height !== ny) {
      canvas = document.createElement("canvas");
      canvas.width = nx;
      canvas.height = ny;
      simCanvasRef.current = canvas;
      simImageRef.current = null;
      if (map.getLayer(SIM_LAYER)) map.removeLayer(SIM_LAYER);
      if (map.getSource(SIM_SOURCE)) map.removeSource(SIM_SOURCE);
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (!simImageRef.current) simImageRef.current = ctx.createImageData(nx, ny);

    if (state.fire) {
      const minutes = state.fire.times[Math.min(state.frame, state.fire.times.length - 1)];
      renderFire(state.fire, minutes, ctx, state.frontMinutes);
    } else if (state.sim) {
      renderFrame(state.sim, state.frame, simImageRef.current, { depthScaleM: state.depthScaleM });
      ctx.putImageData(simImageRef.current, 0, 0);
    }

    const bounds = current.meta.bbox;
    if (!bounds || bounds.length !== 4) return;
    if (!map.getSource(SIM_SOURCE)) {
      map.addSource(SIM_SOURCE, { type: "canvas", canvas, coordinates: bboxCorners(bounds), animate: true });
    }
    const opacity = state.showFlood ? state.opacity : 0;
    if (!map.getLayer(SIM_LAYER)) {
      map.addLayer({
        id: SIM_LAYER,
        type: "raster",
        source: SIM_SOURCE,
        paint: { "raster-opacity": opacity, "raster-fade-duration": 0, "raster-resampling": "linear" },
      });
    } else {
      map.setPaintProperty(SIM_LAYER, "raster-opacity", opacity);
    }
  }

  useEffect(() => {
    if (!containerRef.current || mapRef.current || !TOKEN) return;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: STYLES[useMapStore.getState().baseStyle],
      projection: { name: useMapStore.getState().projection },
      center: [25, 18],
      zoom: 2.1,
    });
    mapRef.current = map;
    if (import.meta.env.DEV) (window as unknown as Record<string, unknown>).__kairosMap = map;

    map.on("style.load", () => {
      applyAtmosphere(map);
      syncTerrain(map);
      ensureAoiLayers(map);
      syncRasterLayers(map);
      syncPointLayers(map);
      syncImageLayers(map);
      syncSimulation(map);
      syncAoi(map);
    });

    const publishViewport = () => {
      const b = map.getBounds();
      if (b) useMapStore.getState().setViewportBbox([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]);
    };
    let spinFrame = 0;
    let lastSpin = performance.now();
    const spin = (now: number) => {
      if (!spinningRef.current) {
        publishViewport();
        return;
      }
      spinFrame = requestAnimationFrame(spin);
      const dt = Math.min(64, now - lastSpin);
      lastSpin = now;
      if (map.isMoving() || map.getZoom() >= 4.5) return;
      const c = map.getCenter();
      map.jumpTo({ center: [c.lng - dt * 0.0035, c.lat] });
    };
    map.once("load", () => {
      lastSpin = performance.now();
      spinFrame = requestAnimationFrame(spin);
    });
    const stopSpin = () => {
      if (!spinningRef.current) return;
      spinningRef.current = false;
      cancelAnimationFrame(spinFrame);
      publishViewport();
    };
    map.on("mousedown", stopSpin);
    map.on("wheel", stopSpin);
    map.on("touchstart", stopSpin);
    map.on("dragstart", stopSpin);

    map.on("click", (e) => {
      const ids = (map.getStyle()?.layers ?? [])
        .map((l) => l.id)
        .filter((id) => id.startsWith("kairos-pts-lyr-") && map.getLayer(id));
      if (!ids.length) return;
      const f = map.queryRenderedFeatures(e.point, { layers: ids }).find((ff) => ff.properties?.title);
      if (!f?.properties) return;
      const p = f.properties as Record<string, string>;
      const meta = [p.category, p.date].filter(Boolean).map(escapeHtml).join(" · ");
      const href = safeHttpUrl(p.link);
      const link = href
        ? `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer" style="color:#00BFA8;text-decoration:none;font-size:10px">Source ↗</a>`
        : "";
      new mapboxgl.Popup({ closeButton: true, maxWidth: "240px" })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div style="font-family:ui-sans-serif,system-ui;color:#E8EFE9">
             <div style="font-size:12px;font-weight:600;margin-bottom:2px">${escapeHtml(p.title)}</div>
             <div style="font-size:10px;color:#8A9E8C;margin-bottom:4px">${meta}</div>
             ${link}
           </div>`
        )
        .addTo(map);
    });

    let coordFrame = 0;
    let pending: { lng: number; lat: number } | null = null;
    map.on("mousemove", (e) => {
      pending = { lng: e.lngLat.lng, lat: e.lngLat.lat };
      if (coordFrame) return;
      coordFrame = requestAnimationFrame(() => {
        coordFrame = 0;
        useMapStore.getState().setCoords(pending);
      });
    });
    map.on("moveend", () => {
      if (!spinningRef.current) publishViewport();
    });

    return () => {
      cancelAnimationFrame(spinFrame);
      cancelAnimationFrame(coordFrame);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (layers.length || pointLayers.length || sim || fire || chatLoading || drawMode) {
      spinningRef.current = false;
    }
  }, [layers, pointLayers, sim, fire, chatLoading, drawMode]);

  useEffect(() => withStyle(mapRef.current, syncRasterLayers), [layers]);
  useEffect(() => withStyle(mapRef.current, syncPointLayers), [pointLayers]);
  useEffect(() => withStyle(mapRef.current, syncImageLayers), [imageLayers]);
  useEffect(() => withStyle(mapRef.current, syncAoi), [aoi, aoiPolygon]);
  useEffect(
    () => withStyle(mapRef.current, syncSimulation),

    [sim, fire, simFrame, simOpacity, simDepthScale, simShowFlood, simFrontMinutes]
  );
  useEffect(() => withStyle(mapRef.current, syncTerrain), [sim, fire, simShowTerrain]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !flyTo) return;
    spinningRef.current = false;
    map.flyTo({ center: flyTo.center, zoom: flyTo.zoom, duration: 2600, essential: true });
  }, [flyTo]);

  const firstStyle = useRef(true);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (firstStyle.current) {
      firstStyle.current = false;
      return;
    }
    map.setStyle(STYLES[baseStyle]);
  }, [baseStyle]);

  useEffect(() => {
    mapRef.current?.setProjection({ name: projection });
  }, [projection]);

  useEffect(() => {
    const map = mapRef.current;
    const container = containerRef.current;
    if (!map || !container) return;
    container.classList.toggle("draw-crosshair", drawMode !== null);
    if (drawMode === null) {
      map.dragPan.enable();
      return;
    }

    if (drawMode === "polygon") {
      map.doubleClickZoom.disable();
      const draft: [number, number][] = [];
      const draftSource = () => map.getSource(DRAFT_SOURCE) as mapboxgl.GeoJSONSource | undefined;
      const render = (preview?: [number, number]) => {
        const pts = preview ? [...draft, preview] : [...draft];
        const features: GeoJSON.Feature[] = draft.map((p) => ({
          type: "Feature",
          properties: {},
          geometry: { type: "Point", coordinates: p },
        }));
        if (pts.length >= 2) {
          features.push({
            type: "Feature",
            properties: {},
            geometry: { type: "LineString", coordinates: pts },
          });
        }
        if (pts.length >= 3) {
          features.push({
            type: "Feature",
            properties: {},
            geometry: { type: "Polygon", coordinates: [[...pts, pts[0]]] },
          });
        }
        draftSource()?.setData({ type: "FeatureCollection", features });
      };
      const clear = () => draftSource()?.setData(EMPTY);
      const finish = () => {
        if (draft.length >= 3) useMapStore.getState().setAoiPolygon([...draft]);
        clear();
        useMapStore.getState().setDrawMode(null);
      };
      const onClick = (e: mapboxgl.MapMouseEvent) => {
        if (draft.length >= 3) {
          const first = map.project(draft[0]);
          if (Math.hypot(first.x - e.point.x, first.y - e.point.y) < 12) {
            finish();
            return;
          }
        }
        draft.push([e.lngLat.lng, e.lngLat.lat]);
        render();
      };
      const onDblClick = (e: mapboxgl.MapMouseEvent) => {
        e.preventDefault();
        finish();
      };
      const onMouseMove = (e: mapboxgl.MapMouseEvent) => {
        if (draft.length) render([e.lngLat.lng, e.lngLat.lat]);
      };
      const onKey = (ev: KeyboardEvent) => {
        if (ev.key === "Escape") {
          clear();
          useMapStore.getState().setDrawMode(null);
        } else if (ev.key === "Enter") {
          finish();
        }
      };
      map.on("click", onClick);
      map.on("dblclick", onDblClick);
      map.on("mousemove", onMouseMove);
      window.addEventListener("keydown", onKey);
      return () => {
        map.off("click", onClick);
        map.off("dblclick", onDblClick);
        map.off("mousemove", onMouseMove);
        window.removeEventListener("keydown", onKey);
        clear();
        map.doubleClickZoom.enable();
      };
    }

    const onDown = (e: mapboxgl.MapMouseEvent) => {
      if (drawMode === "pin" || drawMode === "quickpin") {
        const d = 0.25;
        const store = useMapStore.getState();
        store.setAoi([e.lngLat.lng - d, e.lngLat.lat - d, e.lngLat.lng + d, e.lngLat.lat + d]);
        store.setDrawMode(null);
        if (drawMode === "quickpin") store.setQuickAnalysisOpen(true);
        return;
      }
      map.dragPan.disable();
      drawingRef.current = { start: [e.lngLat.lng, e.lngLat.lat] };
    };
    const onMove = (e: mapboxgl.MapMouseEvent) => {
      if (!drawingRef.current) return;
      const [sx, sy] = drawingRef.current.start;
      useMapStore
        .getState()
        .setAoi([
          Math.min(sx, e.lngLat.lng),
          Math.min(sy, e.lngLat.lat),
          Math.max(sx, e.lngLat.lng),
          Math.max(sy, e.lngLat.lat),
        ]);
    };
    const onUp = () => {
      if (!drawingRef.current) return;
      drawingRef.current = null;
      map.dragPan.enable();
      useMapStore.getState().setDrawMode(null);
    };
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") {
        drawingRef.current = null;
        useMapStore.getState().setDrawMode(null);
      }
    };
    map.on("mousedown", onDown);
    map.on("mousemove", onMove);
    map.on("mouseup", onUp);
    window.addEventListener("keydown", onKey);
    return () => {
      map.off("mousedown", onDown);
      map.off("mousemove", onMove);
      map.off("mouseup", onUp);
      window.removeEventListener("keydown", onKey);
      map.dragPan.enable();
    };
  }, [drawMode]);

  if (!TOKEN) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-bg">
        <div className="max-w-md text-center space-y-3 px-6">
          <p className="font-display text-xl text-ink">Mapbox token missing</p>
          <p className="text-sm text-dim leading-relaxed">
            Copy <span className="font-mono text-teal">frontend/.env.example</span> to{" "}
            <span className="font-mono text-teal">frontend/.env</span>, set{" "}
            <span className="font-mono text-teal">VITE_MAPBOX_TOKEN</span> to your public token from
            account.mapbox.com, then restart <span className="font-mono text-teal">npm run dev</span>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="h-full w-full" role="application" aria-label="Interactive globe" />
  );
}
