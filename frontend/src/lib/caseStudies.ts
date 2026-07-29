import type { BBox } from "../types/map";

export interface CaseStudy {
  id: string;
  title: string;
  place: string;
  when: string;
  hook: string;
  story: string[];
  whatRadarSaw: string;
  analysis_type: string;
  bbox: BBox;
  start_date: string;
  end_date: string;
  runLabel: string;
  caution: string;
}

export const CASE_STUDIES: CaseStudy[] = [
  {
    id: "pakistan-2022",
    title: "The flood that put a third of a country under water",
    place: "Sindh province, Pakistan",
    when: "August 2022",
    hook: "33 million people affected, after a monsoon that dropped many times the normal August rainfall.",
    story: [
      "Through August 2022 Pakistan's monsoon did not let up. In Sindh, whole districts turned into lakes that stayed for months. Around 1,700 people died and millions were displaced.",
      "Relief agencies needed maps quickly, and they needed them under a sky that stayed thick with cloud for weeks. Optical satellites showed grey. Radar did not care.",
      "Sentinel-1 kept passing overhead every few days, sending its own microwave pulse through the cloud deck and timing the echo. Flood water, being flat, reflected that pulse away from the satellite, so it came back almost black.",
    ],
    whatRadarSaw:
      "Farmland that was rough and radar-bright in July read as smooth and dark in August. Subtracting one from the other gives the flood extent directly.",
    analysis_type: "flood_extent",
    bbox: [67.8, 26.4, 69.1, 27.6],
    start_date: "2022-08-20",
    end_date: "2022-09-10",
    runLabel: "Map the Sindh flooding yourself",
    caution:
      "Sindh is heavily irrigated, so some dark pixels are flood water and some are ordinary wet paddy. Running the confounder check on a result like this is the honest next step.",
  },
  {
    id: "hunga-tonga-2022",
    title: "An island that erased itself",
    place: "Hunga Tonga-Hunga Haapai, Tonga",
    when: "January 2022",
    hook: "One of the most violent volcanic explosions in over a century, and the island at the centre of it mostly vanished.",
    story: [
      "On 15 January 2022 an undersea volcano north of Tongatapu erupted hard enough to register on pressure sensors worldwide. The shockwave circled the planet several times and a tsunami reached Japan and Peru.",
      "The eruption also destroyed the island it had spent a decade building. Land that had joined two older islets was blown apart in an afternoon.",
      "Ash filled the air and Tonga's undersea cable was cut, so information was scarce. Radar could still measure the coastline, because it needs neither clear air nor daylight to tell where land stops and water starts.",
    ],
    whatRadarSaw:
      "Land is rough and returns a bright echo; open ocean scatters the pulse away and reads dark. Comparing backscatter before and after shows how much of the island was no longer there.",
    analysis_type: "surface_deformation",
    bbox: [-175.62, -20.65, -175.3, -20.45],
    start_date: "2022-01-10",
    end_date: "2022-02-10",
    runLabel: "Compare the surface before and after",
    caution:
      "This runs the amplitude change detector, not phase interferometry. It shows where the surface changed, not a millimetre measurement of how far it moved.",
  },
  {
    id: "rondonia-clearing",
    title: "The edge of the forest, moving",
    place: "Rondonia, Brazil",
    when: "The 2020 dry season",
    hook: "Clearing follows the roads so regularly that the pattern has a name: fishbone deforestation.",
    story: [
      "Rondonia sits on the southwestern arc of the Amazon, where highways cut into intact forest and side roads branch off them. Land gets cleared in strips beside those roads, which gives satellite images a distinctive fishbone shape.",
      "The clearing season runs through the dry middle of the year. Tracking it with optical imagery means waiting for a cloud-free day, and in the Amazon that wait can run into weeks.",
      "Radar removes the waiting. A forest canopy is a tangle of leaves and branches that scatters the pulse in all directions, some of it back to the satellite, so it reads bright. Strip it to bare ground and the echo drops sharply.",
    ],
    whatRadarSaw:
      "Kairos reads the cross-polarised VH channel, which is especially sensitive to the volume scattering a canopy produces, and flags pixels that fell more than 3 dB below their own 12-month baseline.",
    analysis_type: "deforestation",
    bbox: [-63.6, -9.8, -63.1, -9.4],
    start_date: "2020-06-01",
    end_date: "2020-09-30",
    runLabel: "Find the 2020 clearing",
    caution:
      "Selective logging that leaves the canopy partly standing is much harder to catch than a clear-cut, so a result like this is a floor on the real loss, not a ceiling.",
  },
];
