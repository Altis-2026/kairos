"""Grid conventions, edge resolution, and DEM conditioning."""

import numpy as np
import pytest

from solver import grid


def test_edge_slices_match_the_documented_orientation():
    """Row 0 is north, row -1 south, column 0 west, column -1 east."""
    dem = np.arange(9, dtype=float).reshape(3, 3)
    assert list(dem[grid.EDGES["north"]]) == [0, 1, 2]
    assert list(dem[grid.EDGES["south"]]) == [6, 7, 8]
    assert list(dem[grid.EDGES["west"]]) == [0, 3, 6]
    assert list(dem[grid.EDGES["east"]]) == [2, 5, 8]


def test_lowest_edge_finds_the_outlet():
    dem = np.tile(np.linspace(100.0, 0.0, 10)[:, None], (1, 10))  # drops southward
    assert grid.lowest_edge(dem) == "south"
    assert grid.lowest_edge(dem.T) == "east"


def test_lowest_edge_uses_the_mean_not_one_stray_pixel():
    """One anomalous low pixel on a high wall must not claim the outlet."""
    dem = np.tile(np.linspace(100.0, 0.0, 10)[:, None], (1, 10))
    dem[0, 4] = -500.0
    assert grid.lowest_edge(dem) == "south"


def test_open_edges_are_normalised_and_validated():
    assert grid.validate_edges(None) == ()
    assert grid.validate_edges("south") == ("south",)
    assert grid.validate_edges(["south", "south", "east"]) == ("south", "east")
    with pytest.raises(ValueError, match="Unknown open edge"):
        grid.validate_edges(["downhill"])


def test_pit_filling_removes_an_interior_sink_and_leaves_the_rest_alone():
    dem = np.tile(np.linspace(10.0, 0.0, 12)[:, None], (1, 12))
    dem[6, 6] = -20.0                       # an artefact sink
    before = dem.copy()

    filled = grid.fill_pits(dem)

    assert np.array_equal(dem, before), "fill_pits mutated its input"
    assert filled[6, 6] > -20.0, "the sink was not filled"
    assert np.all(filled >= before - 1e-12), "filling must never lower terrain"
    untouched = np.ones_like(dem, bool)
    untouched[6, 6] = False
    assert filled[untouched] == pytest.approx(before[untouched])


def test_pit_filling_preserves_a_genuine_drainable_valley():
    """A valley that already drains to the border must come back unchanged."""
    dem = np.tile(np.linspace(10.0, 0.0, 12)[:, None], (1, 12))
    assert grid.fill_pits(dem) == pytest.approx(dem)


@pytest.mark.parametrize(
    "dem, dx, message",
    [
        (np.zeros(5), 10.0, "2-D"),
        (np.zeros((2, 8)), 10.0, "at least 3x3"),
        (np.full((5, 5), np.inf), 10.0, "NaN or infinite"),
        (np.zeros((5, 5)), -3.0, "positive, finite cell size"),
    ],
)
def test_grid_validation_rejects_unusable_input(dem, dx, message):
    with pytest.raises(ValueError, match=message):
        grid.check_uniform_grid(dem, dx)
