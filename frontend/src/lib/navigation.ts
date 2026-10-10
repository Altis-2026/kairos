import { useMapStore } from "../stores/mapStore";
import { useSimulationStore } from "../stores/simulationStore";
import type { Route } from "./embed";

type MapSnapshot = Pick<
  ReturnType<typeof useMapStore.getState>,
  "layers" | "pointLayers" | "imageLayers" | "aoi" | "aoiPolygon" | "lastResult"
>;

let workspace: MapSnapshot | null = null;
let simulation: Partial<ReturnType<typeof useSimulationStore.getState>> | null = null;
const MAP_VIEWS: Route[] = ["watch", "guardian", "foresight", "embed"];

export function navigate(route: Route | string) {
  const target = route === "landing" ? "" : route;
  if (location.hash.replace(/^#/, "") === target) return;
  location.hash = target;
  if (!target) history.replaceState(null, "", location.pathname + location.search);
}

export function onRouteChange(from: Route, to: Route) {
  const map = useMapStore.getState();
  if (from === "app" && to !== "app") {
    workspace = {
      layers: map.layers,
      pointLayers: map.pointLayers,
      imageLayers: map.imageLayers,
      aoi: map.aoi,
      aoiPolygon: map.aoiPolygon,
      lastResult: map.lastResult,
    };
  }
  if (MAP_VIEWS.includes(to) || (MAP_VIEWS.includes(from) && to === "app")) {
    useMapStore.setState({
      layers: [],
      pointLayers: [],
      imageLayers: [],
      aoi: null,
      aoiPolygon: null,
      drawMode: null,
      compare: null,
      timeline: null,
    });
  }
  if (to === "app" && workspace) {
    useMapStore.setState(workspace);
    workspace = null;
  }
  const sim = useSimulationStore.getState();
  if (MAP_VIEWS.includes(to) && (sim.sim || sim.fire)) {
    simulation = { sim: sim.sim, fire: sim.fire, status: sim.status, frame: sim.frame };
    useSimulationStore.setState({ sim: null, fire: null, playing: false, view3d: false });
  }
  if (to === "app" && simulation) {
    useSimulationStore.setState(simulation);
    simulation = null;
  }
}
