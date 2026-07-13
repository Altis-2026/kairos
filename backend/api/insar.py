import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "insar")
)

SITES = [
    {
        "id": "mexico-city",
        "name": "Mexico City subsidence",
        "region": "Mexico City, Mexico",
        "bbox": [-99.35, 19.20, -98.85, 19.65],
        "description": (
            "One of the fastest-sinking major cities on Earth. Decades of "
            "groundwater pumping compact the old lakebed clays beneath the "
            "city, and parts of the valley floor drop by tens of centimetres "
            "per year. In the interferogram, each full colour cycle (one "
            "fringe) is about 2.8 cm of ground motion along the satellite's "
            "line of sight between the two acquisition dates."
        ),
        "product": "Sentinel-1 wrapped interferogram and coherence",
        "source": "COMET-LiCSAR (University of Leeds / NERC)",
        "source_url": "https://comet.nerc.ac.uk/comet-lics-portal/",
        "files": {"interferogram": "interferogram.png", "coherence": "coherence.png"},
    },
]

ALLOWED_KINDS = {"interferogram", "coherence"}


def _site_dir(site_id: str) -> str:
    return os.path.join(DATA_DIR, site_id)


def _site_meta(site: dict) -> dict:
    meta_path = os.path.join(_site_dir(site["id"]), "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


def _shape_site(site: dict) -> dict:
    meta = _site_meta(site)
    layers = {}
    for kind, filename in site["files"].items():
        path = os.path.join(_site_dir(site["id"]), filename)
        layers[kind] = f"/insar/data/{site['id']}/{kind}" if os.path.exists(path) else None
    return {
        "id": site["id"],
        "name": site["name"],
        "region": site["region"],
        "bbox": meta.get("bbox", site["bbox"]),
        "description": site["description"],
        "product": site["product"],
        "source": site["source"],
        "source_url": site["source_url"],
        "dates": meta.get("dates"),
        "frame": meta.get("frame"),
        "available": all(layers.values()),
        "layers": layers,
    }


@router.get("/insar/sites")
def insar_sites():
    return {"sites": [_shape_site(s) for s in SITES]}


@router.get("/insar/data/{site_id}/{kind}")
def insar_data(site_id: str, kind: str):
    site = next((s for s in SITES if s["id"] == site_id), None)
    if site is None or kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=404, detail="Unknown InSAR layer.")
    path = os.path.join(_site_dir(site_id), site["files"][kind])
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=(
                "This InSAR dataset is not installed on the server. Run "
                "tools/get_insar_demo.py to download the LiCSAR product."
            ),
        )
    return FileResponse(path, media_type="image/png")
