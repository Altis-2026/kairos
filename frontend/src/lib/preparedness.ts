import type { Hazard } from "../api/foresight";

export interface Playbook {
  before: string[];
  during: string[];
  after: string[];
}

export const PLAYBOOKS: Record<Hazard, Playbook> = {
  flood: {
    before: [
      "Know your evacuation route to higher ground before you need it.",
      "Check whether your address sits in a mapped flood zone (FEMA flood maps are free at msc.fema.gov).",
      "Keep documents, medication and chargers in one grab-bag. Standard home insurance does not cover flooding; that is a separate policy with a 30-day wait.",
      "Sign up for your county's emergency alerts. During the 2025 Texas Hill Country floods, the river rose faster than many warnings traveled.",
    ],
    during: [
      "Never drive through water on a road. Two feet of moving water floats most cars, and depth is unreadable at night.",
      "Move up, not out, if water is rising around the building.",
      "Stay off bridges over fast water and away from storm drains.",
    ],
    after: [
      "Wait for an official all-clear before returning; roads can be undercut below the surface.",
      "Photograph all damage before cleaning up, for insurance.",
      "Treat all floodwater as contaminated; wear gloves and wash anything it touched.",
    ],
  },
  wildfire: {
    before: [
      "Clear dead leaves and brush within 30 feet of the house; embers land in gutters and mulch first.",
      "Plan two ways out of your neighborhood, since fire can close the obvious one.",
      "Pack a go-bag now: documents, medication, N95 masks, chargers.",
      "Know your zone's evacuation terms: 'warning' means get ready, 'order' means leave immediately.",
    ],
    during: [
      "Leave early when an evacuation is ordered. Fire moves faster uphill and with wind than most people expect.",
      "Drive with headlights on and windows shut; smoke can drop visibility to a few meters.",
      "If trapped, call 911, shelter in a cleared area or a building, and stay low where the air is cooler.",
    ],
    after: [
      "Return only after officials open the area; hot spots reignite for days.",
      "Check the roof and gutters for smoldering embers.",
      "Wear an N95 during cleanup; ash carries fine particles deep into lungs.",
    ],
  },
  drought: {
    before: [
      "Fix leaks; a dripping tap wastes thousands of liters a year.",
      "If you garden or farm, shift watering to early morning and mulch soil to hold moisture.",
      "Know your local water restrictions before they tighten.",
    ],
    during: [
      "Follow watering schedules; enforcement usually starts with fines.",
      "Prioritize trees over lawns; grass recovers, mature trees do not.",
      "Dry vegetation is wildfire fuel, so drought weeks are the time to clear defensible space.",
    ],
    after: [
      "Refill slowly: reservoirs and wells recover over seasons, not weeks.",
      "Watch for ground cracks near foundations; clay soils shrink in drought and swell when rain returns.",
    ],
  },
  subsidence: {
    before: [
      "Watch for early signs: doors that stop closing, stair-step cracks in brick, cracks wider at the top.",
      "If your area pumps groundwater heavily, sinking is usually gradual; document baseline photos of walls and floors now.",
      "A structural engineer's inspection costs far less than foundation repair.",
    ],
    during: [
      "Track crack growth with dated pencil marks or photos every few weeks.",
      "Report sudden road or yard depressions to the city; utilities under them fail first.",
    ],
    after: [
      "Get a foundation assessment before repairs; cosmetic patching hides progression.",
      "Ask your insurer what ground-movement coverage you actually have; many policies exclude it.",
    ],
  },
};

export const HAZARD_NAMES: Record<Hazard, string> = {
  flood: "Flooding",
  wildfire: "Wildfire",
  drought: "Drought",
  subsidence: "Sinking ground",
};
