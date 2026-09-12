"""
Fixtures for the simulation pipeline tests.

The whole path — parameter resolution, inflow placement, solve, quantise,
encode, result envelope — is exercised against synthetic terrain through an
injected DEM provider. Nothing here touches Earth Engine, so these run in CI,
on a laptop with no credentials, and in a couple of seconds.
"""

import numpy as np
import pytest

from gee.raster_fetch import DemTile


def synthetic_valley(ny: int = 120, nx: int = 96, dx: float = 30.0) -> np.ndarray:
    """
    A V-shaped valley draining south, with mild noise.

    Real enough to exercise the code that picks an outlet, finds the upstream
    channel, and routes a wave down it — shaped, not random, so the tests
    assert on behaviour rather than on luck.
    """
    rng = np.random.default_rng(20260909)
    centre = (nx - 1) / 2.0
    across = np.abs(np.arange(nx) - centre) / centre
    along = np.linspace(ny * dx * 0.02, 0.0, ny)[:, None]   # 2% downhill, south
    return along + 25.0 * across[None, :] ** 2 + rng.normal(0.0, 0.15, (ny, nx))


@pytest.fixture
def valley_dem():
    return synthetic_valley()


@pytest.fixture
def fake_dem_provider(valley_dem):
    """
    Stands in for `gee.raster_fetch.fetch_dem`.

    Honours the requested scale by reporting it as the cell size, so tests can
    check that the scale parameter actually reaches the solver.
    """

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
    """A small Texas Hill Country box — UTM 14N, no antimeridian games."""
    return [-99.40, 30.02, -99.28, 30.10]
