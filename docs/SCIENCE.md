# The science behind Kairos

## Radar in one page

Sentinel-1 carries a C-band synthetic aperture radar. It sends its own microwave
pulse and measures how much energy returns, called backscatter. Because it
supplies its own illumination at a wavelength that passes through cloud and
smoke, it works day and night in any weather.

Backscatter depends on surface roughness, moisture and geometry:

- Calm water is smooth, so it reflects the pulse away and appears dark.
- Buildings and ship hulls form corner reflectors and appear bright.
- Forest canopy scatters the pulse in every direction, so cross-polarized (VH)
  return is high. Clearing it drops that return sharply.
- Burned vegetation, wet soil and fresh construction each shift the return in
  their own direction.

Most Kairos analyses compare a recent window against a baseline for the same
place and flag pixels whose change goes beyond a threshold. All processing runs
inside Google Earth Engine. Sentinel-1 is always filtered to IW mode and the
right polarization, results are clipped to the area, and every reduction uses
`bestEffort` so large areas stay within memory limits.

## Analyses

| Id | Name | Sensors | Type |
|---|---|---|---|
| `flood_extent` | Flood Extent Mapping | Sentinel-1 | Observed |
| `flood_depth` | Flood Depth Estimation | Sentinel-1, GLO-30 | Observed |
| `flood_consensus` | Flood Consensus (radar and optical) | Sentinel-1, Sentinel-2 | Observed |
| `flooded_forest` | Flooded Forest and Mangrove | Sentinel-1 | Observed |
| `wildfire_burn_scar` | Wildfire Burn Scar Mapping | Sentinel-1 | Observed |
| `fire_fusion` | Wildfire Radar and Thermal Fusion | Sentinel-1, Landsat 8/9 | Observed |
| `building_damage` | Earthquake and Building Damage | Sentinel-1, GHSL | Observed |
| `surface_deformation` | Surface Deformation and Change | Sentinel-1 | Observed |
| `land_subsidence` | Land Subsidence Indicator | Sentinel-1 | Observed |
| `urban_growth` | Urban Growth Monitoring | Sentinel-1 | Observed |
| `deforestation` | Deforestation and Forest Loss | Sentinel-1 | Observed |
| `land_disturbance` | Illegal Mining and Land Disturbance | Sentinel-1 | Observed |
| `forest_biomass` | Forest Biomass and Structure | ALOS PALSAR, Sentinel-2 | Observed |
| `crop_monitoring` | Agriculture and Crop Vigour | Sentinel-1 | Observed |
| `soil_moisture` | Surface Soil Moisture | Sentinel-1 | Observed |
| `ship_detection` | Ship Detection | Sentinel-1 | Observed |
| `oil_spill` | Oil Spill Detection | Sentinel-1 | Observed |
| `ocean_wind` | Ocean Wind (roughness proxy) | Sentinel-1 | Observed |
| `sea_ice` | Sea Ice Extent | Sentinel-1 EW | Observed |
| `ice_drift` | Sea Ice Drift Tracking | Sentinel-1 EW | Observed |
| `wet_snow` | Wet Snow and Melt Extent | Sentinel-1 | Observed |
| `methane` | Methane Monitoring | Sentinel-5P | Observed |
| `air_quality` | Air Quality (NO2) | Sentinel-5P | Observed |
| `archaeology` | Archaeology Mode (L-band anomalies) | ALOS PALSAR | Observed |
| `flood_simulation` | Flood Simulation | GLO-30 | Simulated |
| `fire_simulation` | Wildfire Spread Simulation | GLO-30 | Simulated |

## Uncertainty

Detections that depend on a threshold are computed at several thresholds. The
spread between them becomes a low and high area estimate and lowers the
confidence score when it is wide. Where a cloud-free Sentinel-2 scene exists, an
independent optical index confirms or contradicts the radar result and adjusts
confidence again. A speckle filter is applied before differencing.

## Measured accuracy

The validation module re-runs the production detectors over historical events
that have independent reference maps and reports intersection over union,
precision, recall and F1:

| Benchmark | Reference |
|---|---|
| Brahmaputra floodplain, August 2017 monsoon | Global Flood Database |
| Camp Fire, Butte County, November 2018 | MODIS MCD64A1 burned area |
| Rondonia clearing, 2020 | Hansen Global Forest Change |
| Mississippi River delta vessels, January 2023 | MarineCadastre AIS broadcasts |

Nothing is precomputed. The numbers are produced live each time.

## Confounders

Radar can be fooled. Rain-wet farmland can look like flooding, calm water can
look like oil, and ploughing can look like clearing. The confounder check pulls
CHIRPS rainfall, ERA5 wind and ESA WorldCover land cover for the same place and
window and reports whether an innocent explanation is plausible.

## Flood simulation

The flood model is a local-inertial shallow-water solver (Bates et al. 2010,
de Almeida et al. 2012) on a Copernicus GLO-30 elevation grid. Each step updates
face discharges from the free-surface gradient with Manning friction, then
updates depths from the divergence of those discharges, so the scheme conserves
mass by construction. The time step adapts to the CFL condition. An inflow
hydrograph is placed on the main channel found from the terrain, and the solver
reports mass closure so a broken run cannot pass as a real one. A self-check
detects elevation grids that arrive flipped from Earth Engine.

## Wildfire simulation

Fire behavior uses the Rothermel (1972) surface spread equations with standard
fuel models, live and dead fuel moisture, wind and slope. Spread across the
landscape is solved as a minimum-travel-time problem (Finney 2002): the arrival
time at each cell is the fastest path from the ignition, found exactly with
Dijkstra's algorithm over an elliptical spread pattern. The model covers surface
fire only. It does not model crown fire or spotting, and the app says so.

## Foresight

Exposure scores come from the measured record: historical surface water
occurrence and flood frequency, burned-area history, rainfall deficits and
subsidence signals. Seasonal profiles show which months carry the most risk, and
Mann-Kendall and ordinary least squares tests report whether a trend is
statistically significant. Scores describe history and present exposure, not a
forecast of a specific event.
