/**
 * The Globe — a pure renderer of mapStore.
 *
 * It reads state and renders it; it never owns analysis or UI state.
 * Responsibilities: Mapbox globe projection with the dark-space atmosphere,
 * slow ambient rotation until first interaction, raster/point layer syncing,
 * AOI rectangle drawing, pin drops, coordinate readout, and flyTo requests.
 */
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
};

const AOI_SOURCE = "kairos-aoi";
const AOI_FILL = "kairos-aoi-fill";
const AOI_LINE = "kairos-aoi-line";

function aoiToFeature(bbox: BBox): GeoJSON.Feature {
  const [a, b, c, d] = bbox;
  return {
    type: "Feature",
    properties: {},
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [a, b],
          [c, b],
          [c, d],
          [a, d],
          [a, b],
        ],
      ],
    },
  };
}

/** Space-theme atmosphere per the Kairos design spec. */
function applyAtmosphere(map: mapboxgl.Map) {
  map.setFog({
    color: "rgba(11, 18, 14, 0.9)",
    "high-color": "rgba(0, 191, 168, 0.12)",
    "horizon-blend": 0.04,
    "space-color": "#070d0a",
    "star-intensity": 0.35,
  });
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
}

export default function Globe() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const spinningRef = useRef(true);
  const drawingRef = useRef<{ start: [number, number] } | null>(null);

  const layers = useMapStore((s) => s.layers);
  const pointLayers = useMapStore((s) => s.pointLayers);
  const aoi = useMapStore((s) => s.aoi);
  const drawMode = useMapStore((s) => s.drawMode);
  const flyTo = useMapStore((s) => s.flyTo);
  const baseStyle = useMapStore((s) => s.baseStyle);

  // ---------- map init (once) ----------
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: STYLES.satellite,
      projection: { name: "globe" },
      center: [25, 18],
      zoom: 2.1,
    });
    mapRef.current = map;

    map.on("style.load", () => {
      applyAtmosphere(map);
      ensureAoiLayers(map);
      // Re-sync everything after any style swap
      syncRasterLayers(map);
      syncPointLayers(map);
      syncAoi(map);
    });

    // Ambient rotation until the user touches the globe
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

    // Coordinate readout + viewport tracking
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------- layer sync helpers (read latest store inside) ----------
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
    // Remove layers deleted from the store
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
            "circle-radius": 4,
            "circle-color": layer.color,
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
    const current = useMapStore.getState().aoi;
    const source = map.getSource(AOI_SOURCE) as mapboxgl.GeoJSONSource | undefined;
    source?.setData(
      current
        ? { type: "FeatureCollection", features: [aoiToFeature(current)] }
        : { type: "FeatureCollection", features: [] }
    );
  }

  // ---------- react to store changes ----------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    syncRasterLayers(map);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layers]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    syncPointLayers(map);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pointLayers]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    syncAoi(map);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aoi]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !flyTo) return;
    spinningRef.current = false;
    map.flyTo({ center: flyTo.center, zoom: flyTo.zoom, duration: 2600, essential: true });
  }, [flyTo]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.setStyle(STYLES[baseStyle]); // 'style.load' handler re-syncs everything
  }, [baseStyle]);

  // ---------- AOI drawing (click-drag rectangle / click pin) ----------
  useEffect(() => {
    const map = mapRef.current;
    const container = containerRef.current;
    if (!map || !container) return;

    container.classList.toggle("draw-crosshair", drawMode !== null);

    if (drawMode === null) {
      map.dragPan.enable();
      return;
    }

    const onDown = (e: mapboxgl.MapMouseEvent) => {
      if (drawMode === "pin") {
        const d = 0.25; // ~25 km half-box around the pin
        useMapStore
          .getState()
          .setAoi([
            e.lngLat.lng - d,
            e.lngLat.lat - d,
            e.lngLat.lng + d,
            e.lngLat.lat + d,
          ]);
        useMapStore.getState().setDrawMode(null);
        return;
      }
      // rectangle: begin drag
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
