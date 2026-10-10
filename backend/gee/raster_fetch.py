import hashlib
import io
import math
import os
from dataclasses import dataclass

import numpy as np

GLO30 = "COPERNICUS/DEM/GLO30"

MAX_CELLS = 1_000_000

DEFAULT_SCALE_M = 30.0

_CACHE_VERSION = 2


@dataclass
class DemTile:
    dem: np.ndarray
    dx: float
    crs: str
    bbox: list
    source: str = GLO30
    cached: bool = False
    origin_easting: float | None = None
    origin_northing: float | None = None
    void_fraction: float = 0.0

    @property
    def shape(self) -> tuple:
        return self.dem.shape

    def as_dict(self) -> dict:
        ny, nx = self.dem.shape
        return {
            "dem_source": self.source,
            "dem_crs": self.crs,
            "dem_scale_m": self.dx,
            "dem_shape": [ny, nx],
            "dem_min_m": float(self.dem.min()),
            "dem_max_m": float(self.dem.max()),
            "dem_cached": self.cached,
            "dem_origin_easting": self.origin_easting,
            "dem_origin_northing": self.origin_northing,
            "dem_void_fraction": round(self.void_fraction, 6),
            "dem_note": (
                "Copernicus GLO-30 is a digital *surface* model: canopy and "
                "buildings are part of the elevation, so flow is routed around "
                "structures rather than through them."
            ),
        }


def utm_epsg(lon: float, lat: float) -> str:
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} is outside [-90, 90].")
    wrapped = ((lon + 180.0) % 360.0) - 180.0
    zone = int((wrapped + 180.0) / 6.0) + 1
    zone = min(max(zone, 1), 60)
    hemisphere = 326 if lat >= 0 else 327
    return f"EPSG:{hemisphere}{zone:02d}"


def bbox_extent_m(bbox: list) -> tuple:
    min_lon, min_lat, max_lon, max_lat = bbox
    mid_lat = math.radians((min_lat + max_lat) / 2.0)
    width = (max_lon - min_lon) * 111_320.0 * math.cos(mid_lat)
    height = (max_lat - min_lat) * 110_540.0
    return abs(width), abs(height)


@dataclass
class GridPlan:
    crs: str
    scale_m: float
    nx: int
    ny: int
    requested_scale_m: float
    downscaled: bool

    @property
    def cells(self) -> int:
        return self.nx * self.ny


def plan_grid(
    bbox: list,
    scale_m: float = DEFAULT_SCALE_M,
    max_cells: int = MAX_CELLS,
    allow_coarsen: bool = True,
) -> GridPlan:
    if scale_m <= 0:
        raise ValueError(f"scale_m must be positive; got {scale_m}.")
    if max_cells < 100:
        raise ValueError(f"max_cells must be at least 100; got {max_cells}.")

    width_m, height_m = bbox_extent_m(bbox)
    if width_m <= 0 or height_m <= 0:
        raise ValueError(f"Degenerate AOI {bbox}: it has no area.")

    centre_lon = (bbox[0] + bbox[2]) / 2.0
    centre_lat = (bbox[1] + bbox[3]) / 2.0
    crs = utm_epsg(centre_lon, centre_lat)

    scale = float(scale_m)
    cells = (width_m / scale) * (height_m / scale)
    downscaled = False
    if cells > max_cells:
        if not allow_coarsen:
            km2 = width_m * height_m / 1e6
            raise ValueError(
                f"This area ({km2:.0f} km²) needs {cells:,.0f} cells at "
                f"{scale_m:.0f} m, over the {max_cells:,} cell limit. Draw a "
                f"smaller box, or request a coarser scale (try "
                f"{math.ceil(scale * math.sqrt(cells / max_cells)):.0f} m)."
            )
        scale = scale * math.sqrt(cells / max_cells)
        downscaled = True

    nx = max(int(width_m / scale), 3)
    ny = max(int(height_m / scale), 3)
    return GridPlan(
        crs=crs,
        scale_m=scale,
        nx=nx,
        ny=ny,
        requested_scale_m=float(scale_m),
        downscaled=downscaled,
    )


def cache_key(bbox: list, plan: GridPlan, source: str) -> str:
    payload = f"v{_CACHE_VERSION}|{source}|{plan.crs}|{plan.scale_m:.4f}|{plan.nx}x{plan.ny}|" + ",".join(
        f"{c:.6f}" for c in bbox
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def _cache_dir() -> str:
    return os.getenv("KAIROS_RASTER_CACHE", os.path.join("data", "raster_cache"))


def _load_cached(path: str):
    try:
        with np.load(path) as bundle:
            return bundle["dem"], float(bundle["void_fraction"])
    except Exception:
        return None


def _store_cached(path: str, dem: np.ndarray, void_fraction: float) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez_compressed(path, dem=dem, void_fraction=void_fraction)
    except Exception:
        pass


ORIENTATION_TOLERANCE_M = 20.0


def check_orientation(dem: np.ndarray, corner_elevations: dict) -> None:
    ny, nx = dem.shape
    array_corners = {
        "nw": dem[0, 0],
        "ne": dem[0, nx - 1],
        "sw": dem[ny - 1, 0],
        "se": dem[ny - 1, nx - 1],
    }
    mismatches = []
    for corner, expected in corner_elevations.items():
        actual = array_corners[corner]
        if not np.isfinite(expected):
            continue
        diff = abs(actual - expected)
        if diff > ORIENTATION_TOLERANCE_M:
            mismatches.append(f"{corner}: array={actual:.1f}m independent={expected:.1f}m (diff {diff:.1f}m)")

    if mismatches:
        raise ValueError(
            "DEM orientation check failed. The fetched array does not match "
            "independently-sampled elevation at its own corners, which means "
            "the grid is misaligned, flipped, or transposed rather than just "
            "noisy (tolerance is " + f"{ORIENTATION_TOLERANCE_M:.0f}m). "
            "Routing water on this grid would silently run it the wrong way. "
            "Mismatches: " + "; ".join(mismatches)
        )


def _sample_corners(image, crs: str, corners: dict) -> dict:
    import ee  # noqa: PLC0415, mirrors fetch_dem's lazy import; see docstring.

    result = {}
    for name, (x, y) in corners.items():
        point = ee.Geometry.Point([x, y], crs)
        value = image.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=30,
        ).get("DEM")
        got = value.getInfo()
        result[name] = float(got) if got is not None else float("nan")
    return result


def fetch_dem(
    bbox: list,
    scale_m: float = DEFAULT_SCALE_M,
    max_cells: int = MAX_CELLS,
    allow_coarsen: bool = True,
    use_cache: bool = True,
) -> DemTile:
    plan = plan_grid(bbox, scale_m, max_cells, allow_coarsen=allow_coarsen)

    path = os.path.join(_cache_dir(), f"glo30-{cache_key(bbox, plan, GLO30)}.npz")
    if use_cache:
        hit = _load_cached(path)
        if hit is not None:
            dem, void_fraction = hit
            return DemTile(
                dem=dem,
                dx=plan.scale_m,
                crs=plan.crs,
                bbox=list(bbox),
                cached=True,
                void_fraction=void_fraction,
            )

    import ee  # noqa: PLC0415, deliberately lazy; see docstring.

    from gee import common  # noqa: PLC0415, pulls in ee at import time.

    common.bbox_geometry(bbox)

    image = ee.ImageCollection(GLO30).select("DEM").mosaic()

    corner = ee.Geometry.Point([bbox[0], bbox[1]]).transform(plan.crs, 1)
    x0, y0 = corner.coordinates().getInfo()
    top = float(y0) + plan.ny * plan.scale_m

    try:
        encoded = ee.data.computePixels(
            {
                "expression": image,
                "fileFormat": "NPY",
                "bandIds": ["DEM"],
                "grid": {
                    "dimensions": {"width": plan.nx, "height": plan.ny},
                    "affineTransform": {
                        "scaleX": plan.scale_m,
                        "shearX": 0.0,
                        "translateX": float(x0),
                        "shearY": 0.0,
                        "scaleY": -plan.scale_m,
                        "translateY": top,
                    },
                    "crsCode": plan.crs,
                },
            }
        )
    except Exception as exc:
        raise ValueError(
            f"Earth Engine could not return elevation pixels for this area "
            f"({plan.nx}x{plan.ny} at {plan.scale_m:.0f} m in {plan.crs}): {exc}"
        ) from exc

    structured = np.load(io.BytesIO(encoded), allow_pickle=False)
    dem = np.asarray(structured["DEM"], dtype=np.float64)
    if dem.size == 0:
        raise ValueError(f"No GLO-30 elevation data covers {bbox}.")

    finite_mask = np.isfinite(dem)
    void_fraction = float((~finite_mask).mean())
    if void_fraction > 0.0:
        if not finite_mask.any():
            raise ValueError(
                f"GLO-30 returned no valid elevations for {bbox}. The AOI is probably entirely over water."
            )
        dem = np.where(finite_mask, dem, float(dem[finite_mask].min()))

    half = plan.scale_m / 2.0
    corner_points = {
        "nw": (x0 + half, top - half),
        "ne": (x0 + plan.nx * plan.scale_m - half, top - half),
        "sw": (x0 + half, top - plan.ny * plan.scale_m + half),
        "se": (x0 + plan.nx * plan.scale_m - half, top - plan.ny * plan.scale_m + half),
    }
    independent = _sample_corners(image, plan.crs, corner_points)
    check_orientation(dem, independent)

    if use_cache:
        _store_cached(path, dem, void_fraction)

    return DemTile(
        dem=dem,
        dx=plan.scale_m,
        crs=plan.crs,
        bbox=list(bbox),
        origin_easting=float(x0),
        origin_northing=top,
        void_fraction=void_fraction,
    )
