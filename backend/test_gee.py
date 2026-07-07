import os
import ee
from dotenv import load_dotenv

load_dotenv()

project = os.getenv("GOOGLE_CLOUD_PROJECT")
if not project:
    raise SystemExit("Set GOOGLE_CLOUD_PROJECT in backend/.env first.")

ee.Initialize(project=project)
count = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(ee.Geometry.Rectangle([88.0, 20.0, 92.0, 24.0]))
    .size()
    .getInfo()
)
print(f"Found {count} Sentinel-1 images over Bangladesh. GEE is working.")
