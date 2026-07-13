HOTSPOTS = [
    {
        "id": "rondonia-deforestation",
        "region": "Rondônia, Brazil",
        "analysis_type": "deforestation",
        "bbox": [-64.2, -11.6, -62.8, -10.4],
    },
    {
        "id": "hormuz-ships",
        "region": "Strait of Hormuz",
        "analysis_type": "ship_detection",
        "bbox": [55.6, 26.0, 56.9, 27.0],
    },
    {
        "id": "malacca-ships",
        "region": "Strait of Malacca",
        "analysis_type": "ship_detection",
        "bbox": [102.9, 1.1, 104.1, 2.0],
    },
    {
        "id": "niger-delta-oil",
        "region": "Niger Delta, Nigeria",
        "analysis_type": "oil_spill",
        "bbox": [5.8, 4.1, 7.2, 5.0],
    },
    {
        "id": "bengal-delta-flood",
        "region": "Ganges Delta, Bangladesh",
        "analysis_type": "flood_extent",
        "bbox": [89.4, 22.6, 90.8, 23.8],
    },
    {
        "id": "jakarta-subsidence",
        "region": "Jakarta, Indonesia",
        "analysis_type": "land_subsidence",
        "bbox": [106.6, -6.4, 107.1, -6.0],
    },
    {
        "id": "svalbard-ice",
        "region": "Svalbard, Arctic Ocean",
        "analysis_type": "sea_ice",
        "bbox": [12.0, 76.4, 21.0, 79.2],
    },
    {
        "id": "central-valley-crops",
        "region": "Central Valley, California",
        "analysis_type": "crop_monitoring",
        "bbox": [-120.6, 36.2, -119.4, 37.2],
    },
    {
        "id": "madre-de-dios-mining",
        "region": "Madre de Dios, Peru",
        "analysis_type": "land_disturbance",
        "bbox": [-70.6, -13.2, -69.6, -12.4],
    },
    {
        "id": "cairo-urban",
        "region": "Greater Cairo, Egypt",
        "analysis_type": "urban_growth",
        "bbox": [31.0, 29.8, 31.9, 30.3],
    },
]

WINDOW_DAYS = {
    "ship_detection": 10,
    "oil_spill": 14,
    "flood_extent": 30,
    "wildfire_burn_scar": 30,
    "sea_ice": 30,
    "deforestation": 45,
    "land_disturbance": 45,
    "crop_monitoring": 30,
    "urban_growth": 60,
    "land_subsidence": 120,
    "surface_deformation": 30,
    "building_damage": 21,
}

MIN_HEADLINE = {
    "flood_extent": 5.0,
    "wildfire_burn_scar": 5.0,
    "deforestation": 1.0,
    "oil_spill": 0.5,
    "ship_detection": 3.0,
    "land_disturbance": 0.5,
    "urban_growth": 0.5,
    "land_subsidence": 0.5,
    "surface_deformation": 1.0,
    "building_damage": 0.5,
    "sea_ice": 1.0,
    "crop_monitoring": 0.01,
}

EONET_ANALYSIS = {
    "floods": "flood_extent",
    "wildfires": "wildfire_burn_scar",
    "severeStorms": "flood_extent",
    "seaLakeIce": "sea_ice",
    "earthquakes": "building_damage",
    "volcanoes": "surface_deformation",
    "landslides": "surface_deformation",
    "drought": "crop_monitoring",
}
