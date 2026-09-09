"""
Grid planning for the DEM fetch.

`fetch_dem` itself needs Earth Engine, but everything that decides *what* to
ask for is pure arithmetic — and it is the part that can be silently wrong, so
it is the part that is tested.
"""

import math
import sys

import numpy as np
import pytest

from gee import raster_fetch as rf


def test_module_imports_without_earth_engine():
    """
    The fetch module must be importable with no credentials and no `ee`.

    Everything downstream (the solver orchestrator, the registry, the tests)
    imports it, so a module-level `import ee` here would make the whole
    simulation path undevelopable offline.
    """
    assert "gee.raster_fetch" in sys.modules
    source = open(rf.__file__).read()
    assert "\nimport ee" not in source, "ee must be imported lazily, inside fetch_dem"


class TestUtmZone:
    """
    The projection fix. A lat/lon grid has cells that shrink with latitude,
    which routes water at a wrong angle everywhere off the equator — with
    nothing in the output that looks wrong. Requesting a metric CRS is what
    prevents it, so the zone arithmetic gets pinned down here.
    """

    @pytest.mark.parametrize(
        "lon, lat, expected",
        [
            (-112.09, 36.10, "EPSG:32612"),   # Grand Canyon, UTM 12N
            (-99.34, 30.07, "EPSG:32614"),    # Texas Hill Country, 14N
            (89.70, 24.45, "EPSG:32645"),     # Jamuna, Bangladesh, 45N
            (-58.44, -34.60, "EPSG:32721"),   # Buenos Aires, 21S
            (0.0, 51.5, "EPSG:32631"),        # Greenwich, 31N
            (-179.9, 64.0, "EPSG:32601"),     # far west, zone 1
            (179.9, -41.0, "EPSG:32760"),     # far east, zone 60
        ],
    )
    def test_known_zones(self, lon, lat, expected):
        assert rf.utm_epsg(lon, lat) == expected

    def test_equator_resolves_north(self):
        assert rf.utm_epsg(10.0, 0.0).startswith("EPSG:326")

    def test_longitudes_are_wrapped_not_clamped(self):
        assert rf.utm_epsg(190.0, 10.0) == rf.utm_epsg(-170.0, 10.0)

    def test_impossible_latitude_is_rejected(self):
        with pytest.raises(ValueError, match="outside"):
            rf.utm_epsg(0.0, 120.0)


class TestGridPlanning:
    def test_extent_shrinks_with_latitude(self):
        """
        The reason UTM is needed at all: the same degree span is a different
        number of metres wide at different latitudes.
        """
        equator, _ = rf.bbox_extent_m([0.0, 0.0, 1.0, 1.0])
        high, _ = rf.bbox_extent_m([0.0, 60.0, 1.0, 61.0])
        assert high == pytest.approx(equator * math.cos(math.radians(60.5)), rel=0.02)

    def test_plan_matches_the_requested_scale_when_it_fits(self):
        plan = rf.plan_grid([-99.40, 30.02, -99.28, 30.10], scale_m=30.0)
        assert plan.crs == "EPSG:32614"
        assert plan.scale_m == 30.0
        assert not plan.downscaled
        assert 300 < plan.nx < 400 and 250 < plan.ny < 350

    def test_oversized_aoi_is_coarsened_to_fit_the_cap(self):
        plan = rf.plan_grid([0.0, 0.0, 2.0, 2.0], scale_m=10.0, max_cells=50_000)
        assert plan.downscaled
        assert plan.scale_m > plan.requested_scale_m
        assert plan.cells <= 50_000 * 1.02   # integer rounding of nx/ny

    def test_oversized_aoi_can_refuse_instead_of_coarsening(self):
        """
        The API path uses this: quietly returning something coarser than the
        user asked for is worse than telling them the box is too big.
        """
        with pytest.raises(ValueError, match="cell limit"):
            rf.plan_grid([0.0, 0.0, 2.0, 2.0], scale_m=10.0, max_cells=50_000,
                         allow_coarsen=False)

    def test_error_message_suggests_a_workable_scale(self):
        with pytest.raises(ValueError) as excinfo:
            rf.plan_grid([0.0, 0.0, 1.0, 1.0], scale_m=10.0, max_cells=10_000,
                         allow_coarsen=False)
        assert "smaller box" in str(excinfo.value)

    def test_a_grid_is_never_degenerate(self):
        plan = rf.plan_grid([0.0, 0.0, 0.0002, 0.0002], scale_m=30.0)
        assert plan.nx >= 3 and plan.ny >= 3

    @pytest.mark.parametrize(
        "bbox, scale, message",
        [
            ([0.0, 0.0, 1.0, 1.0], -5.0, "scale_m must be positive"),
            ([0.0, 0.0, 0.0, 1.0], 30.0, "no area"),
        ],
    )
    def test_bad_plans_are_rejected(self, bbox, scale, message):
        with pytest.raises(ValueError, match=message):
            rf.plan_grid(bbox, scale_m=scale)


class TestCacheKey:
    def test_is_stable_for_identical_requests(self):
        bbox = [-99.40, 30.02, -99.28, 30.10]
        plan = rf.plan_grid(bbox)
        assert rf.cache_key(bbox, plan, rf.GLO30) == rf.cache_key(bbox, plan, rf.GLO30)

    def test_changes_with_the_area(self):
        a, b = [-99.40, 30.02, -99.28, 30.10], [-99.41, 30.02, -99.28, 30.10]
        assert rf.cache_key(a, rf.plan_grid(a), rf.GLO30) != rf.cache_key(
            b, rf.plan_grid(b), rf.GLO30
        )

    def test_changes_with_the_resolution(self):
        bbox = [-99.40, 30.02, -99.28, 30.10]
        assert rf.cache_key(bbox, rf.plan_grid(bbox, 30.0), rf.GLO30) != rf.cache_key(
            bbox, rf.plan_grid(bbox, 60.0), rf.GLO30
        )


class TestTileCache:
    """
    Re-running the same AOI is the normal case in a demo, so the cache is what
    makes the second run instant. It must never be the reason a request fails.
    """

    def test_round_trips_the_array_and_the_void_fraction(self, tmp_path):
        dem = np.linspace(0.0, 100.0, 48).reshape(6, 8)
        path = str(tmp_path / "tile.npz")

        rf._store_cached(path, dem, 0.125)
        loaded, void_fraction = rf._load_cached(path)

        assert np.array_equal(loaded, dem)
        assert void_fraction == 0.125

    def test_a_missing_or_corrupt_entry_is_a_miss_not_a_crash(self, tmp_path):
        assert rf._load_cached(str(tmp_path / "absent.npz")) is None

        corrupt = tmp_path / "corrupt.npz"
        corrupt.write_bytes(b"this is not a numpy archive")
        assert rf._load_cached(str(corrupt)) is None

    def test_an_unwritable_cache_directory_is_survivable(self):
        """A read-only filesystem must degrade to no caching, not to an error."""
        rf._store_cached("/proc/definitely/not/writable/tile.npz", np.zeros((3, 3)), 0.0)


class TestTileMetadata:
    def test_reports_the_surface_model_caveat_and_the_projection(self):
        """
        GLO-30 includes canopy and buildings, and the grid is metric rather
        than lat/lon. Both belong in the result, not in a comment.
        """
        tile = rf.DemTile(
            dem=np.zeros((4, 4)), dx=30.0, crs="EPSG:32614",
            bbox=[-99.4, 30.0, -99.3, 30.1], origin_easting=1.0,
            origin_northing=2.0, void_fraction=0.02,
        )
        meta = tile.as_dict()
        assert meta["dem_crs"] == "EPSG:32614"
        assert meta["dem_scale_m"] == 30.0
        assert meta["dem_void_fraction"] == 0.02
        assert "surface* model" in meta["dem_note"]
        assert meta["dem_shape"] == [4, 4]


class TestOrientationGuard:
    """
    The guard for the one failure mode in this module that does not fail
    loudly on its own: a wrong affine (flipped axis, transposed array) still
    returns a full, plausible-looking DEM — just with north and south, or
    east and west, swapped. Fed to the solver, that produces a confidently
    wrong animation (water flowing uphill), not a crash. This is what makes
    that impossible to ship silently.
    """

    def test_a_correctly_oriented_array_passes(self):
        dem = np.array([[100.0, 90.0], [80.0, 70.0]])
        rf.check_orientation(dem, {"nw": 100.0, "ne": 90.0, "sw": 80.0, "se": 70.0})

    def test_matches_within_tolerance_for_ordinary_resampling_noise(self):
        dem = np.array([[100.0, 90.0], [80.0, 70.0]])
        rf.check_orientation(
            dem, {"nw": 105.0, "ne": 88.0, "sw": 81.0, "se": 73.0}
        )   # all within 20 m

    def test_a_north_south_flip_is_caught(self):
        """The exact bug this exists to catch: rows reversed."""
        dem = np.array([[400.0, 300.0], [200.0, 100.0]])   # nw/ne swapped with sw/se
        with pytest.raises(ValueError, match="orientation check failed"):
            rf.check_orientation(dem, {"nw": 200.0, "ne": 100.0, "sw": 400.0, "se": 300.0})

    def test_an_east_west_flip_is_caught(self):
        dem = np.array([[400.0, 300.0], [200.0, 100.0]])
        with pytest.raises(ValueError, match="orientation check failed"):
            rf.check_orientation(dem, {"nw": 300.0, "ne": 400.0, "sw": 100.0, "se": 200.0})

    def test_a_transposition_is_caught(self):
        dem = np.array([[400.0, 300.0], [200.0, 100.0]])
        with pytest.raises(ValueError, match="orientation check failed"):
            rf.check_orientation(dem, {"nw": 400.0, "ne": 200.0, "sw": 300.0, "se": 100.0})

    def test_the_failing_corners_are_named_in_the_message(self):
        """A partial mismatch (one corner off) must say which one, not just
        that something disagreed — that's the difference between a five
        second diagnosis and re-deriving the whole affine by hand."""
        dem = np.array([[100.0, 90.0], [80.0, 70.0]])
        with pytest.raises(ValueError, match="ne: array=90"):
            rf.check_orientation(dem, {"nw": 100.0, "ne": 500.0, "sw": 80.0, "se": 70.0})

    def test_a_void_at_the_sampled_corner_is_not_treated_as_a_mismatch(self):
        """
        GLO-30 has ocean voids; an independent sample can legitimately land on
        one. NaN there is "no signal", not "signal of a bug" — it must not
        block a real AOI whose corner happens to be over water.
        """
        dem = np.array([[100.0, 90.0], [80.0, 70.0]])
        rf.check_orientation(
            dem, {"nw": float("nan"), "ne": 90.0, "sw": 80.0, "se": 70.0}
        )

    def test_the_end_to_end_fetch_path_calls_the_guard(self, monkeypatch):
        """
        The guard existing as a function is not the point — it has to run on
        every live fetch, unconditionally, or it protects nothing. This drives
        `fetch_dem` with `ee` and `common` faked out and asserts the guard
        actually fires and actually blocks a bad result.
        """
        import sys
        import types

        dem_array = np.array([[400.0, 300.0], [200.0, 100.0]], dtype=np.float32)
        structured = np.zeros(dem_array.shape, dtype=[("DEM", "f4")])
        structured["DEM"] = dem_array
        import io as _io
        buf = _io.BytesIO()
        np.save(buf, structured)
        npy_bytes = buf.getvalue()

        fake_ee = types.SimpleNamespace()
        fake_ee.data = types.SimpleNamespace(computePixels=lambda spec: npy_bytes)

        class FakeGeom:
            def transform(self, crs, err):
                return self
            def coordinates(self):
                return self
            def getInfo(self):
                return [500000.0, 4000000.0]

        fake_ee.Geometry = types.SimpleNamespace(
            Rectangle=lambda bbox: None, Point=lambda *a, **k: FakeGeom()
        )
        fake_ee.ImageCollection = lambda name: types.SimpleNamespace(
            select=lambda band: types.SimpleNamespace(mosaic=lambda: "fake_image")
        )
        fake_ee.Reducer = types.SimpleNamespace(first=lambda: "first")

        monkeypatch.setitem(sys.modules, "ee", fake_ee)

        # Patch the attribute on the real, already-imported gee.common module
        # rather than swapping sys.modules["gee.common"] for a fake one:
        # `from gee import common` inside fetch_dem binds to whatever object
        # is already attached as `gee.common` once any other test in this
        # process has imported it for real, so a sys.modules swap done here
        # would be silently bypassed. Patching the attribute in place works
        # regardless of import order.
        from gee import common as real_common
        monkeypatch.setattr(real_common, "bbox_geometry", lambda bbox: None)

        # Correctly-oriented independent samples: fetch_dem must succeed.
        monkeypatch.setattr(
            rf, "_sample_corners",
            lambda image, crs, corners: {"nw": 400.0, "ne": 300.0, "sw": 200.0, "se": 100.0},
        )
        tile = rf.fetch_dem([0.0, 0.0, 0.001, 0.001], scale_m=30.0, use_cache=False)
        assert tile.dem.shape == (2, 2)

        # Flipped independent samples: fetch_dem must refuse to return data.
        monkeypatch.setattr(
            rf, "_sample_corners",
            lambda image, crs, corners: {"nw": 200.0, "ne": 100.0, "sw": 400.0, "se": 300.0},
        )
        with pytest.raises(ValueError, match="orientation check failed"):
            rf.fetch_dem([0.0, 0.0, 0.001, 0.001], scale_m=30.0, use_cache=False)
