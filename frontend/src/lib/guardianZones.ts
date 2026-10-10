import type { BBox } from "../types/map";

export interface GuardianZone {
  id: string;
  name: string;
  country: string;

  brief: string;

  watchingFor: string;
  analysisType: string;
  bbox: BBox;
  center: [number, number];
  threat: "mining" | "logging" | "fishing" | "spill";
}

export const GUARDIAN_ZONES: GuardianZone[] = [
  {
    id: "madre-de-dios",
    name: "Madre de Dios",
    country: "Peru",
    brief:
      "Illegal alluvial gold mining has stripped tens of thousands of hectares of " +
      "Amazon rainforest along these rivers, leaving toxic mercury ponds behind.",
    watchingFor: "Fresh forest clearing and new settling ponds",
    analysisType: "land_disturbance",
    bbox: [-70.35, -13.0, -69.95, -12.7],
    center: [-70.15, -12.85],
    threat: "mining",
  },
  {
    id: "yanomami",
    name: "Yanomami Territory",
    country: "Brazil",
    brief:
      "Thousands of illegal miners (garimpeiros) have invaded this protected " +
      "Indigenous reserve in Roraima, polluting rivers and clearing forest.",
    watchingFor: "New clearings and mining ponds inside the reserve",
    analysisType: "land_disturbance",
    bbox: [-63.6, 2.0, -63.2, 2.35],
    center: [-63.4, 2.18],
    threat: "mining",
  },
  {
    id: "borneo-clearing",
    name: "Central Kalimantan",
    country: "Indonesia",
    brief:
      "Borneo's peat rainforest is cleared for palm oil and timber, often " +
      "illegally and under haze that hides it from optical satellites.",
    watchingFor: "Recent forest loss against a 12-month baseline",
    analysisType: "deforestation",
    bbox: [113.4, -2.2, 113.8, -1.85],
    center: [113.6, -2.02],
    threat: "logging",
  },
  {
    id: "galapagos-edge",
    name: "Galápagos Reserve Edge",
    country: "Ecuador",
    brief:
      "Industrial fishing fleets mass at the boundary of this marine reserve, " +
      "and some cross in with their tracking transponders switched off.",
    watchingFor: "Vessels clustered near the protected boundary",
    analysisType: "ship_detection",
    bbox: [-91.9, -1.3, -91.4, -0.85],
    center: [-91.65, -1.07],
    threat: "fishing",
  },
  {
    id: "gulf-of-guinea",
    name: "Gulf of Guinea Shelf",
    country: "West Africa EEZ",
    brief:
      "West Africa loses billions to illegal, unreported fishing; trawlers work " +
      "national waters that local fleets depend on.",
    watchingFor: "Vessels over the coastal fishing shelf",
    analysisType: "ship_detection",
    bbox: [3.0, 4.3, 3.5, 4.75],
    center: [3.25, 4.52],
    threat: "fishing",
  },
  {
    id: "niger-delta",
    name: "Niger Delta",
    country: "Nigeria",
    brief:
      "Pipeline tapping and spills repeatedly foul the creeks and coastal waters " +
      "of one of the world's largest wetlands.",
    watchingFor: "Dark slicks that flatten the water's radar return",
    analysisType: "oil_spill",
    bbox: [5.6, 4.3, 6.1, 4.75],
    center: [5.85, 4.52],
    threat: "spill",
  },
];
