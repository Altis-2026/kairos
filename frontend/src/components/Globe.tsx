import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useMapStore } from "../stores/mapStore";
import type { BBox } from "../types/map";

const TOKEN = (import.meta.env.VITE_MAPBOX_TOKEN as string) || "";
mapboxgl.accessToken = TOKEN;

const STYLES = {
  satellite: "mapbox://styles/mapbox/satellite-streets-v12",
  dark: "mapbox://styles/mapbox/dark-v11",
  terrain: "mapbox://styles/mapbox/outdoors-v12",
};

const DEM_SOURCE = "kairos-dem";

const AOI_SOURCE = "kairos-aoi";
const AOI_FILL = "kairos-aoi-fill";
const AOI_LINE = "kairos-aoi-line";
const DRAFT_SOURCE = "kairos-aoi-draft";
const DRAFT_LINE = "kairos-aoi-draft-line";
const DRAFT_FILL = "kairos-aoi-draft-fill";
const DRAFT_POINTS = "kairos-aoi-draft-points";

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
  return {
    type: "Feature",
    properties: {},
    geometry: { type: "Polygon", coordinates: [coords] },
  };
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
  if (style === "terrain") {
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

function ensureAoiLayers(map: mapboxgl.Map) {
  if (!map.getSource(AOI_SOURCE)) {
    map.addSource(AOI_SOURCE, {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
  }
  if (!map.getLayer(AOI_FILL)) {
    map.addLayer({
      id: AOI_FILL,
      type: "fill",
      source: AOI_SOURCE,
      paint: { "fill-color": "#E8A318", "fill-opacity": 0.08 },
    });
  }
  if (!map.getLayer(AOI_LINE)) {
    map.addLayer({
      id: AOI_LINE,
      type: "line",
      source: AOI_SOURCE,
      paint: {
        "line-color": "#E8A318",
        "line-width": 1.5,
        "line-dasharray": [2, 1.5],
      },
    });
  }
  if (!map.getSource(DRAFT_SOURCE)) {
    map.addSource(DRAFT_SOURCE, {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
  }
  if (!map.getLayer(DRAFT_FILL)) {
    map.addLayer({
      id: DRAFT_FILL,
      type: "fill",
      source: DRAFT_SOURCE,
      filter: ["==", "$type", "Polygon"],
      paint: { "fill-color": "#E8A318", "fill-opacity": 0.06 },
    });
  }
  if (!map.getLayer(DRAFT_LINE)) {
    map.addLayer({
      id: DRAFT_LINE,
      type: "line",
      source: DRAFT_SOURCE,
      filter: ["==", "$type", "LineString"],
      paint: {
        "line-color": "#E8A318",
        "line-width": 1.5,
        "line-dasharray": [1.5, 1.5],
      },
    });
  }
  if (!map.getLayer(DRAFT_POINTS)) {
    map.addLayer({
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
    });
  }
}

export default function Globe() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const spinningRef = useRef(true);
  const drawingRef = useRef<{ start: [number, number] } | null>(null);

  const layers = useMapStore((s) => s.layers);
  const pointLayers = useMapStore((s) => s.pointLayers);
  const aoi = useMapStore((s) => s.aoi);
  const aoiPolygon = useMapStore((s) => s.aoiPolygon);
  const drawMode = useMapStore((s) => s.drawMode);
  const flyTo = useMapStore((s) => s.flyTo);
  const baseStyle = useMapStore((s) => s.baseStyle);
  const projection = useMapStore((s) => s.projection);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: STYLES.satellite,
      projection: { name: useMapStore.getState().projection },
      center: [25, 18],
      zoom: 2.1,
    });
    mapRef.current = map;

    map.on("style.load", () => {
      applyAtmosphere(map);
      syncTerrain(map);
      ensureAoiLayers(map);

      syncRasterLayers(map);
      syncPointLayers(map);
      syncAoi(map);
    });

    const spin = () => {
      if (!spinningRef.current || !mapRef.current) return;
      const m = mapRef.current;
      if (m.getZoom() < 4.5) {
        m.easeTo({
          center: [m.getCenter().lng - 0.35, m.getCenter().lat],
          duration: 1000,
          easing: (t) => t,
        });
      }
    };
    map.on("moveend", spin);
    const stopSpin = () => {
      spinningRef.current = false;
    };
    map.on("mousedown", stopSpin);
    map.on("wheel", stopSpin);
    map.on("touchstart", stopSpin);
    map.on("load", spin);

    map.on("click", (e) => {
      const ptLayerIds = (map.getStyle()?.layers ?? [])
        .map((l) => l.id)
        .filter((id) => id.startsWith("kairos-pts-lyr-") && map.getLayer(id));
      if (!ptLayerIds.length) return;
      const feats = map.queryRenderedFeatures(e.point, { layers: ptLayerIds });
      const f = feats.find((ff) => ff.properties && ff.properties.title);
      if (!f || !f.properties) return;
      const p = f.properties as Record<string, string>;
      const meta = [p.category, p.date].filter(Boolean).join(" · ");
      const link = p.link
        ? `<a href="${p.link}" target="_blank" rel="noreferrer" style="color:#00BFA8;text-decoration:none;font-size:10px">Source ↗</a>`
        : "";
      new mapboxgl.Popup({ closeButton: true, maxWidth: "240px" })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div style="font-family:ui-sans-serif,system-ui;color:#E8EFE9">
             <div style="font-size:12px;font-weight:600;margin-bottom:2px">${p.title}</div>
             <div style="font-size:10px;color:#8A9E8C;margin-bottom:4px">${meta}</div>
             ${link}
           </div>`
        )
        .addTo(map);
    });

    map.on("mousemove", (e) => {
      useMapStore.getState().setCoords({ lng: e.lngLat.lng, lat: e.lngLat.lat });
    });
    map.on("moveend", () => {
      const b = map.getBounds();
      if (b) {
        useMapStore
          .getState()
          .setViewportBbox([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]);
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };

  }, []);

  function syncRasterLayers(map: mapboxgl.Map) {
    const current = useMapStore.getState().layers;
    for (const layer of current) {
      const srcId = `kairos-src-${layer.id}`;
      const lyrId = `kairos-lyr-${layer.id}`;
      if (!map.getSource(srcId)) {
        map.addSource(srcId, {
          type: "raster",
          tiles: [layer.tileUrl],
          tileSize: 256,
        });
      }
      if (!map.getLayer(lyrId)) {
        map.addLayer({ id: lyrId, type: "raster", source: srcId });
      }
      map.setPaintProperty(lyrId, "raster-opacity", layer.visible ? layer.opacity : 0);
    }

    const wanted = new Set(current.map((l) => `kairos-lyr-${l.id}`));
    for (const l of map.getStyle()?.layers ?? []) {
      if (l.id.startsWith("kairos-lyr-") && !wanted.has(l.id)) {
        map.removeLayer(l.id);
        const srcId = l.id.replace("kairos-lyr-", "kairos-src-");
        if (map.getSource(srcId)) map.removeSource(srcId);
      }
    }
  }

  function syncPointLayers(map: mapboxgl.Map) {
    const current = useMapStore.getState().pointLayers;
    for (const layer of current) {
      const srcId = `kairos-pts-src-${layer.id}`;
      const lyrId = `kairos-pts-lyr-${layer.id}`;
      if (!map.getSource(srcId)) {
        map.addSource(srcId, { type: "geojson", data: layer.data });
      }
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
    const wanted = new Set(current.map((l) => `kairos-pts-lyr-${l.id}`));
    for (const l of map.getStyle()?.layers ?? []) {
      if (l.id.startsWith("kairos-pts-lyr-") && !wanted.has(l.id)) {
        map.removeLayer(l.id);
        const srcId = l.id.replace("kairos-pts-lyr-", "kairos-pts-src-");
        if (map.getSource(srcId)) map.removeSource(srcId);
      }
    }
  }

  function syncAoi(map: mapboxgl.Map) {
    ensureAoiLayers(map);
    const { aoi: current, aoiPolygon } = useMapStore.getState();
    const source = map.getSource(AOI_SOURCE) as mapboxgl.GeoJSONSource | undefined;
    source?.setData(
      current
        ? { type: "FeatureCollection", features: [aoiToFeature(current, aoiPolygon)] }
        : { type: "FeatureCollection", features: [] }
    );
  }

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    syncRasterLayers(map);

  }, [layers]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    syncPointLayers(map);

  }, [pointLayers]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    syncAoi(map);

  }, [aoi, aoiPolygon]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !flyTo) return;
    spinningRef.current = false;
    map.flyTo({ center: flyTo.center, zoom: flyTo.zoom, duration: 2600, essential: true });
  }, [flyTo]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.setStyle(STYLES[baseStyle]);
  }, [baseStyle]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.setProjection({ name: projection });
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

      const renderDraft = (preview?: [number, number]) => {
        const src = map.getSource(DRAFT_SOURCE) as mapboxgl.GeoJSONSource | undefined;
        if (!src) return;
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
        src.setData({ type: "FeatureCollection", features });
      };

      const clearDraft = () => {
        const src = map.getSource(DRAFT_SOURCE) as mapboxgl.GeoJSONSource | undefined;
        src?.setData({ type: "FeatureCollection", features: [] });
      };

      const finish = () => {
        if (draft.length >= 3) {
          useMapStore.getState().setAoiPolygon([...draft]);
        }
        clearDraft();
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
        renderDraft();
      };

      const onDblClick = (e: mapboxgl.MapMouseEvent) => {
        e.preventDefault();
        finish();
      };

      const onMouseMove = (e: mapboxgl.MapMouseEvent) => {
        if (draft.length > 0) renderDraft([e.lngLat.lng, e.lngLat.lat]);
      };

      const onKey = (ev: KeyboardEvent) => {
        if (ev.key === "Escape") {
          clearDraft();
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
        clearDraft();
        map.doubleClickZoom.enable();
      };
    }

    const onDown = (e: mapboxgl.MapMouseEvent) => {
      if (drawMode === "pin" || drawMode === "quickpin") {
        const d = 0.25;
        const store = useMapStore.getState();
        store.setAoi([
          e.lngLat.lng - d,
          e.lngLat.lat - d,
          e.lngLat.lng + d,
          e.lngLat.lat + d,
        ]);
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
      const bbox: BBox = [
        Math.min(sx, e.lngLat.lng),
        Math.min(sy, e.lngLat.lat),
        Math.max(sx, e.lngLat.lng),
        Math.max(sy, e.lngLat.lat),
      ];
      useMapStore.getState().setAoi(bbox);
    };

    const onUp = () => {
      if (!drawingRef.current) return;
      drawingRef.current = null;
      map.dragPan.enable();
      useMapStore.getState().setDrawMode(null);
    };

    map.on("mousedown", onDown);
    map.on("mousemove", onMove);
    map.on("mouseup", onUp);
    return () => {
      map.off("mousedown", onDown);
      map.off("mousemove", onMove);
      map.off("mouseup", onUp);
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
            <span className="font-mono text-teal">frontend/.env</span> and set{" "}
            <span className="font-mono text-teal">VITE_MAPBOX_TOKEN</span> to your
            public token from account.mapbox.com, then restart{" "}
            <span className="font-mono text-teal">npm run dev</span>.
          </p>
        </div>
      </div>
    );
  }

  return <div ref={containerRef} className="h-full w-full" />;
}
