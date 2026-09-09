"""
Synthetic terrain fixtures.

Every test in this package runs on generated terrain rather than a real DEM:
the numerics must be verifiable with no Earth Engine credentials, no network,
and no fixture files. Each generator is deterministic.
"""

import numpy as np
import pytest


@pytest.fixture
def bowl():
    """
    A closed parabolic basin.

    Rim at 10 m, floor at 0 m. Water placed anywhere inside must stay inside,
    which makes this the reference case for mass conservation and settling.
    """

    def _bowl(n: int = 40, rim: float = 10.0) -> np.ndarray:
        ax = np.linspace(-1.0, 1.0, n)
        yy, xx = np.meshgrid(ax, ax, indexing="ij")
        return rim * np.minimum(xx**2 + yy**2, 1.0)

    return _bowl


@pytest.fixture
def two_basins():
    """
    Two basins separated by a north-south ridge across the middle.

    The ridge is the regression guard for face reconstruction: a solver that
    approximates the free surface as a flat plane, or that forgets to subtract
    the higher bed elevation at a face, will leak water over a ridge it should
    never cross.
    """

    def _two_basins(
        n: int = 41, ridge_height: float = 5.0, floor: float = 0.0
    ) -> np.ndarray:
        dem = np.full((n, n), floor, dtype=np.float64)
        dem[:, 0] = dem[:, -1] = ridge_height * 2
        dem[0, :] = dem[-1, :] = ridge_height * 2
        mid = n // 2
        dem[:, mid - 1 : mid + 2] = ridge_height
        return dem

    return _two_basins


@pytest.fixture
def noisy_slope():
    """
    A steep, noisy tilted plane — the worst case for an explicit scheme.

    Steep free-surface gradients and abrupt cell-to-cell elevation changes are
    exactly what destabilise a local-inertial solver, so this is the terrain
    the stability test uses.
    """

    def _noisy_slope(
        n: int = 48, drop: float = 60.0, noise: float = 1.5, seed: int = 20260909
    ) -> np.ndarray:
        rng = np.random.default_rng(seed)
        base = np.linspace(drop, 0.0, n)[:, None] * np.ones((1, n))
        return base + rng.normal(0.0, noise, size=(n, n))

    return _noisy_slope


@pytest.fixture
def tilted_channel():
    """
    A gently sloping valley draining south — the shape a real event runs on.

    A V-shaped cross-section so water concentrates in a channel rather than
    sheeting uniformly, with the south edge lowest so it is the natural outlet.
    """

    def _tilted_channel(ny: int = 40, nx: int = 30, slope: float = 0.01,
                        dx: float = 30.0, banks: float = 6.0) -> np.ndarray:
        centre = (nx - 1) / 2.0
        across = np.abs(np.arange(nx) - centre) / centre
        along = np.arange(ny)[:, None] * dx * slope
        return (along[::-1] + banks * across[None, :] ** 2).astype(np.float64)

    return _tilted_channel
