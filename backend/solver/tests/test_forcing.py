import numpy as np
import pytest

from solver import forcing


def test_hydrograph_integrates_exactly_over_a_whole_event():
    times, values = forcing.validate_hydrograph([(0.0, 0.0), (600.0, 120.0), (1800.0, 120.0), (3600.0, 0.0)])
    expected = 0.5 * 600 * 120 + 1200 * 120 + 0.5 * 1800 * 120
    got = forcing.integrate_hydrograph(times, values, 0.0, 3600.0)
    assert got == pytest.approx(expected, rel=1e-12)


def test_integration_is_exact_across_a_breakpoint():
    times, values = forcing.validate_hydrograph([(0.0, 0.0), (100.0, 100.0), (200.0, 0.0)])
    straddling = forcing.integrate_hydrograph(times, values, 50.0, 150.0)
    assert straddling == pytest.approx(0.5 * (50 + 100) * 50 + 0.5 * (100 + 50) * 50, rel=1e-12)


def test_integration_is_additive_over_subintervals():
    times, values = forcing.validate_hydrograph([(0.0, 5.0), (250.0, 90.0), (900.0, 10.0), (1500.0, 0.0)])
    whole = forcing.integrate_hydrograph(times, values, 0.0, 1500.0)
    pieces = sum(
        forcing.integrate_hydrograph(times, values, a, b)
        for a, b in zip(np.linspace(0, 1500, 37)[:-1], np.linspace(0, 1500, 37)[1:])
    )
    assert pieces == pytest.approx(whole, rel=1e-12)


def test_discharge_is_held_constant_outside_the_hydrograph_span():
    times, values = forcing.validate_hydrograph([(0.0, 10.0), (100.0, 40.0)])
    assert forcing.sample_hydrograph(times, values, -50.0) == 10.0
    assert forcing.sample_hydrograph(times, values, 500.0) == 40.0


@pytest.mark.parametrize(
    "bad, message",
    [
        ([], "empty"),
        ([(0.0, 1.0), (0.0, 2.0)], "strictly increasing"),
        ([(0.0, 1.0), (-10.0, 2.0)], "strictly increasing"),
        ([(0.0, -5.0)], "non-negative"),
        ([(0.0, np.nan)], "NaN"),
    ],
)
def test_malformed_hydrographs_are_rejected(bad, message):
    with pytest.raises(ValueError, match=message):
        forcing.validate_hydrograph(bad)


def test_rainfall_conversion():
    assert forcing.rainfall_rate(36.0) == pytest.approx(1e-5)
    assert forcing.rainfall_rate(0.0) == 0.0
    with pytest.raises(ValueError):
        forcing.rainfall_rate(-1.0)


def test_inflow_lands_on_the_lowest_cells_near_the_point():
    dem = np.ones((20, 20)) * 50.0
    dem[9:12, 8] = 1.0
    mask = forcing.lowest_cells_mask(dem, row=10, col=9, n_cells=3, radius=3)

    assert mask.sum() == 3
    assert mask[9:12, 8].all(), "inflow was not placed in the channel"


def test_inflow_point_outside_the_domain_is_rejected():
    with pytest.raises(ValueError, match="outside"):
        forcing.lowest_cells_mask(np.zeros((10, 10)), row=10, col=5)


def test_inflow_mask_shape_is_checked():
    with pytest.raises(ValueError, match="does not match"):
        forcing.validate_inflow_mask(np.zeros((4, 4), bool), (8, 8))
