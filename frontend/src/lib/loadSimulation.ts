import { runSimulation, type SimulationKind } from "../api/simulate";
import { bboxCenterZoom, useMapStore } from "../stores/mapStore";
import { useSimulationStore } from "../stores/simulationStore";
import { decodeSimulation } from "./simulation";
import { decodeFire } from "./fire";
import type { BBox } from "../types/map";
import type { FirePayload, SimulationPayload } from "../types/simulation";

interface SimulatedResult {
  analysis_type: string;
  bbox: number[];
  simulation?: unknown;
}

export async function loadSimulationResult(result: SimulatedResult) {
  const store = useSimulationStore.getState();
  if (!result.simulation) throw new Error("The simulation returned no frames.");
  if (result.analysis_type === "fire_simulation") {
    store.setProgressNote("Decoding arrival times…");
    store.loadFire(decodeFire(result.simulation as FirePayload));
  } else {
    store.setProgressNote("Decoding frames…");
    store.loadSimulation(await decodeSimulation(result.simulation as SimulationPayload));
  }
  const { center, zoom } = bboxCenterZoom(result.bbox as BBox);
  useMapStore.getState().requestFlyTo(center, zoom);
}

export async function simulateHere(kind: SimulationKind, bbox: BBox) {
  const store = useSimulationStore.getState();
  store.setStatus("running");
  store.setProgressNote("Fetching terrain…");
  try {
    const result = await runSimulation({ kind, bbox }, (note) =>
      useSimulationStore.getState().setProgressNote(note)
    );
    await loadSimulationResult(result);
  } catch (e) {
    store.setStatus("error", e instanceof Error ? e.message : "Simulation failed.");
    throw e;
  }
}
