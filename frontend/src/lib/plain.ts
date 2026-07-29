function area(value: number): string {
  if (value >= 100) return `about ${Math.round(value).toLocaleString()} square kilometers`;
  if (value >= 1) return `about ${value.toFixed(1)} square kilometers`;
  if (value > 0) return "under a square kilometer";
  return "no measurable area";
}

function fields(value: number): string {
  const f = Math.round((value * 1_000_000) / 7000);
  if (f >= 2 && value < 20) return ` That is roughly ${f.toLocaleString()} soccer fields.`;
  return "";
}

export function plainSentence(
  analysisType: string,
  value: number,
  dataDate: string
): string {
  const none = value === 0;
  switch (analysisType) {
    case "flood_extent":
      return none
        ? "No new flooding shows up in this area for these dates."
        : `Water is covering land that is normally dry: ${area(value)} of new flooding.${fields(value)}`;
    case "flood_depth":
      return none
        ? "No flood depth signal here for these dates."
        : `Flooded ground here is estimated at around ${value.toFixed(1)} meters deep in the deepest zones.`;
    case "ship_detection":
      return none
        ? "No vessels showed up on the most recent radar pass."
        : `${Math.round(value).toLocaleString()} vessels were visible on the most recent radar pass.`;
    case "wildfire_burn_scar":
      return none
        ? "No fresh burn scar is visible for these dates."
        : `Fire has left its mark: ${area(value)} of freshly burned ground.${fields(value)}`;
    case "fire_fusion":
      return none
        ? "No burn scar or active hotspots detected for these dates."
        : `${area(value)} shows burn damage, checked against heat readings from a second satellite.`;
    case "oil_spill":
      return none
        ? "No slick-like patches on the water here."
        : `${area(value)} of the water surface looks unusually smooth, the way oil flattens waves. Wind can fake this, so check the conditions note.`;
    case "deforestation":
      return none
        ? "No fresh tree loss detected in this window."
        : `Trees are coming down: ${area(value)} of forest loss in this window.${fields(value)}`;
    case "sea_ice":
      return none
        ? "No sea ice detected in this area."
        : `Sea ice covers ${area(value)} of this area.`;
    case "ice_drift":
      return none
        ? "The ice here is not moving measurably."
        : `The ice here is drifting about ${value.toFixed(1)} kilometers per day.`;
    case "surface_deformation":
      return none
        ? "The ground surface looks stable across these dates."
        : `${area(value)} of ground surface changed in a way that outlasts normal noise.`;
    case "building_damage":
      return none
        ? "No building damage signature detected."
        : `${area(value)} of built-up area shows damage-like radar change.`;
    case "land_subsidence":
      return none
        ? "No steady sinking or rising trend detected here."
        : `${area(value)} shows a steady, one-direction change over time, the kind sinking ground produces.`;
    case "urban_growth":
      return none
        ? "No new construction detected in this window."
        : `New construction is appearing: ${area(value)} of fresh built-up area.${fields(value)}`;
    case "crop_monitoring":
      return `Crop vigor here averages ${value.toFixed(2)} on a 0 to 1 scale; higher means denser, healthier vegetation.`;
    case "land_disturbance":
      return none
        ? "No fresh land disturbance detected."
        : `${area(value)} of ground was freshly disturbed, the pattern informal mining and clearing leave behind.`;
    case "ocean_wind":
      return `Winds over this water average about ${value.toFixed(1)} meters per second (${Math.round(value * 2.237)} mph).`;
    case "soil_moisture":
      return `Soil here sits at ${value.toFixed(2)} on a dry-to-wet scale of 0 to 1, judged against its own yearly range.`;
    case "air_quality":
      return `Nitrogen dioxide, the exhaust gas from traffic and industry, averages ${value.toFixed(1)} units over this area. Higher numbers mean more combustion pollution.`;
    case "methane":
      return `The methane reading here averages ${value.toFixed(0)} parts per billion; zones well above that are flagged as possible leak areas.`;
    default:
      return `The reading for this analysis is ${value.toLocaleString()} as of ${dataDate}.`;
  }
}

export function plainConfidence(confidence: number): string {
  const pct = Math.round(confidence * 100);
  if (pct >= 85) return `Kairos is quite sure about this one (${pct}% confidence).`;
  if (pct >= 65) return `Reasonably solid, worth a second look (${pct}% confidence).`;
  return `Treat this as a first hint, not a conclusion (${pct}% confidence).`;
}
