import numpy as np
import pytest

from gee.raster_fetch import DemTile


def synthetic_valley(ny: int = 120, nx: int = 96, dx: float = 30.0) -> np.ndarray:
    rng = np.random.default_rng(20260909)
    centre = (nx - 1) / 2.0
    across = np.abs(np.arange(nx) - centre) / centre
    along = np.linspace(ny * dx * 0.02, 0.0, ny)[:, None]
    return along + 25.0 * across[None, :] ** 2 + rng.normal(0.0, 0.15, (ny, nx))


@pytest.fixture
def valley_dem():
    return synthetic_valley()


@pytest.fixture
def fake_dem_provider(valley_dem):

    def _provider(bbox, scale_m):
        return DemTile(
            dem=valley_dem.copy(),
            dx=float(scale_m),
            crs="EPSG:32614",
            bbox=list(bbox),
            cached=False,
        )

    return _provider


@pytest.fixture
def aoi():
    return [-99.40, 30.02, -99.28, 30.10]


@pytest.fixture(autouse=True)
def _fresh_rate_limits_and_cache():
    import ratelimit
    import result_cache

    ratelimit.reset()
    result_cache.clear()
    yield
