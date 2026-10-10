import numpy as np
import pytest


@pytest.fixture
def bowl():

    def _bowl(n: int = 40, rim: float = 10.0) -> np.ndarray:
        ax = np.linspace(-1.0, 1.0, n)
        yy, xx = np.meshgrid(ax, ax, indexing="ij")
        return rim * np.minimum(xx**2 + yy**2, 1.0)

    return _bowl


@pytest.fixture
def two_basins():

    def _two_basins(n: int = 41, ridge_height: float = 5.0, floor: float = 0.0) -> np.ndarray:
        dem = np.full((n, n), floor, dtype=np.float64)
        dem[:, 0] = dem[:, -1] = ridge_height * 2
        dem[0, :] = dem[-1, :] = ridge_height * 2
        mid = n // 2
        dem[:, mid - 1 : mid + 2] = ridge_height
        return dem

    return _two_basins


@pytest.fixture
def noisy_slope():

    def _noisy_slope(n: int = 48, drop: float = 60.0, noise: float = 1.5, seed: int = 20260909) -> np.ndarray:
        rng = np.random.default_rng(seed)
        base = np.linspace(drop, 0.0, n)[:, None] * np.ones((1, n))
        return base + rng.normal(0.0, noise, size=(n, n))

    return _noisy_slope


@pytest.fixture
def tilted_channel():

    def _tilted_channel(
        ny: int = 40, nx: int = 30, slope: float = 0.01, dx: float = 30.0, banks: float = 6.0
    ) -> np.ndarray:
        centre = (nx - 1) / 2.0
        across = np.abs(np.arange(nx) - centre) / centre
        along = np.arange(ny)[:, None] * dx * slope
        return (along[::-1] + banks * across[None, :] ** 2).astype(np.float64)

    return _tilted_channel
