import os
import threading
import time

import gee_ready

STORIES = [
    {
        "id": "hill-country-2025",
        "title": "Texas Hill Country floods",
        "place": "Kerr County, Texas",
        "when": "July 2025",
        "summary": "The Guadalupe River rose about 26 feet in under an hour. Radar maps the water that cloud cover hid from cameras.",
        "analysis_type": "flood_extent",
        "bbox": [-99.45, 29.95, -98.95, 30.15],
        "start_date": "2025-07-03",
        "end_date": "2025-07-12",
    },
    {
        "id": "pakistan-2022",
        "title": "Pakistan monsoon floods",
        "place": "Sindh, Pakistan",
        "when": "August 2022",
        "summary": "A third of the country under water and weeks of cloud. Sentinel-1 kept measuring the whole time.",
        "analysis_type": "flood_extent",
        "bbox": [67.8, 26.4, 69.1, 27.6],
        "start_date": "2022-08-20",
        "end_date": "2022-09-10",
    },
    {
        "id": "lahaina-2023",
        "title": "Lahaina wildfire",
        "place": "Maui, Hawaii",
        "when": "August 2023",
        "summary": "The burn scar of the deadliest US wildfire in a century, read through the smoke.",
        "analysis_type": "wildfire_burn_scar",
        "bbox": [-156.71, 20.84, -156.6, 20.93],
        "start_date": "2023-08-08",
        "end_date": "2023-08-25",
    },
    {
        "id": "antakya-2023",
        "title": "Turkey earthquake damage",
        "place": "Antakya, Turkey",
        "when": "February 2023",
        "summary": "Where buildings stopped reflecting radar the way they did the week before the earthquake.",
        "analysis_type": "building_damage",
        "bbox": [36.1, 36.17, 36.22, 36.25],
        "start_date": "2023-02-06",
        "end_date": "2023-02-20",
    },
    {
        "id": "rondonia-clearing",
        "title": "Amazon clearing",
        "place": "Rondonia, Brazil",
        "when": "2020 dry season",
        "summary": "The fishbone pattern of roads and clearing, caught without waiting for a cloud-free day.",
        "analysis_type": "deforestation",
        "bbox": [-63.6, -9.8, -63.1, -9.4],
        "start_date": "2020-06-01",
        "end_date": "2020-09-30",
    },
    {
        "id": "hunga-tonga-2022",
        "title": "Hunga Tonga eruption",
        "place": "Tonga",
        "when": "January 2022",
        "summary": "An island that blew itself apart, measured by how the radar echo of its coastline changed.",
        "analysis_type": "surface_deformation",
        "bbox": [-175.62, -20.65, -175.3, -20.45],
        "start_date": "2022-01-10",
        "end_date": "2022-02-10",
    },
]

BY_ID = {s["id"]: s for s in STORIES}
REFRESH_HOURS = float(os.getenv("FEATURED_REFRESH_HOURS", "5"))
_status: dict = {}


def run_story(story_id: str) -> dict:
    from api.analyze import run_analysis

    story = BY_ID[story_id]
    return run_analysis(
        analysis_type=story["analysis_type"],
        bbox=story["bbox"],
        start_date=story["start_date"],
        end_date=story["end_date"],
    )


def status() -> dict:
    return dict(_status)


def _warm_all():
    import result_cache

    result_cache.clear()
    for story in STORIES:
        try:
            run_story(story["id"])
            _status[story["id"]] = "ready"
        except Exception as e:
            _status[story["id"]] = f"unavailable: {e}"


def _loop():
    gee_ready.ready.wait()
    if gee_ready.error:
        return
    while True:
        _warm_all()
        time.sleep(REFRESH_HOURS * 3600)


def start_warmer():
    if os.getenv("FEATURED_WARM_ENABLED", "1") not in ("1", "true", "yes"):
        return
    threading.Thread(target=_loop, daemon=True).start()
