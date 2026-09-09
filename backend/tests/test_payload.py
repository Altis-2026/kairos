"""
Frame payload: decimation, quantisation, and the round trip the browser makes.

Two properties matter here. The terrain and the water must come out on the
*same* grid, or the 3D viewer's water mesh will not sit on its terrain mesh.
And the decimation must not bias the numbers a user reads off the map.
"""

import base64

import numpy as np
import pytest

from solver import solve
from solver.payload import (
    DEPTH_SCALE,
    block_mean,
    decode_simulation,
    encode_simulation,
    payload_bytes,
    quantize_depth,
    transport_factor,
)
from tests.conftest import synthetic_valley


@pytest.fixture(scope="module")
def solved():
    dem = synthetic_valley(ny=140, nx=110)
    mask = np.zeros(dem.shape, dtype=bool)
    mask[1, 53:58] = True
    return solve(
        dem, 30.0, inflow_mask=mask,
        hydrograph=[(0.0, 0.0), (600.0, 150.0), (2400.0, 0.0)],
        duration_s=5400.0, n_frames=12, open_edges="auto", fill_dem_pits=True,
    )


class TestDecimation:
    @pytest.mark.parametrize(
        "shape, max_dim, expected",
        [((100, 100), 256, 1), ((300, 300), 256, 2), ((512, 400), 256, 2),
         ((1000, 200), 256, 4), ((256, 256), 256, 1)],
    )
    def test_factor_brings_the_longest_edge_under_the_cap(self, shape, max_dim, expected):
        assert transport_factor(shape, max_dim) == expected

    def test_block_mean_preserves_the_average(self):
        """
        Area-averaging is unbiased. Taking the block maximum instead — the
        other obvious choice — would inflate every depth the user reads.
        """
        rng = np.random.default_rng(3)
        arr = rng.random((60, 40)) * 5.0
        assert block_mean(arr, 4).mean() == pytest.approx(arr.mean(), rel=1e-12)

    def test_block_mean_is_a_no_op_at_factor_one(self):
        arr = np.arange(12.0).reshape(3, 4)
        assert np.array_equal(block_mean(arr, 1), arr)

    def test_ragged_edges_are_dropped_not_partially_averaged(self):
        """Every output cell must cover the same ground area as its neighbours."""
        arr = np.ones((11, 7))
        assert block_mean(arr, 3).shape == (3, 2)


class TestQuantisation:
    def test_depth_round_trips_to_within_half_a_centimetre(self):
        depth = np.array([[0.0, 0.004, 1.234, 12.5]])
        recovered = quantize_depth(depth).astype(float) / DEPTH_SCALE
        assert np.abs(recovered - depth).max() <= 0.5 / DEPTH_SCALE

    def test_negative_depth_cannot_wrap_around(self):
        """
        uint16 underflow would turn a -1 cm rounding artefact into 655 m of
        water. The solver should never produce one, but the codec must not be
        the thing that turns it into a catastrophe if it ever does.
        """
        assert quantize_depth(np.array([[-0.01, -5.0]])).max() == 0

    def test_absurd_depth_saturates_instead_of_wrapping(self):
        assert quantize_depth(np.array([[1e6]]))[0, 0] == 65535


class TestEncodedPayload:
    def test_terrain_and_water_share_one_grid(self, solved):
        payload = encode_simulation(solved, max_transport_dim=64)
        dem, depths = decode_simulation(payload)
        assert dem.shape == depths.shape[1:], "water mesh would not match terrain"
        assert depths.shape[0] == payload["meta"]["n_frames"] == len(solved.times)

    def test_round_trip_recovers_the_decimated_fields(self, solved):
        payload = encode_simulation(solved, max_transport_dim=64)
        dem, depths = decode_simulation(payload)
        factor = payload["meta"]["transport_factor"]

        assert np.abs(dem - block_mean(solved.dem, factor)).max() < 1e-3   # float32
        for i in (0, len(solved.depths) // 2, -1):
            expected = block_mean(solved.depths[i], factor)
            assert np.abs(depths[i] - expected).max() <= 0.5 / DEPTH_SCALE

    def test_meta_reports_both_grids_so_no_one_has_to_guess(self, solved):
        payload = encode_simulation(solved, max_transport_dim=64)
        meta = payload["meta"]
        factor = meta["transport_factor"]
        assert meta["solve_dx"] == solved.dx
        assert meta["dx"] == solved.dx * factor
        assert meta["solve_shape"] == list(solved.dem.shape)

    def test_payload_carries_the_simulated_label_and_the_ledger(self, solved):
        payload = encode_simulation(solved, max_transport_dim=64)
        assert payload["meta"]["mode"] == "simulated"
        assert "volume" in payload["meta"]
        assert abs(payload["meta"]["volume"]["mass_error"]) < 1e-12

    def test_byte_lengths_match_the_declared_shapes(self, solved):
        """Guards against an endianness or dtype change silently breaking the
        client, which reads these as raw typed arrays."""
        payload = encode_simulation(solved, max_transport_dim=64)
        meta = payload["meta"]
        cells = meta["ny"] * meta["nx"]
        assert len(base64.b64decode(payload["dem_b64"])) == cells * 4      # float32
        assert len(base64.b64decode(payload["depth_b64"])) == (
            cells * meta["n_frames"] * 2                                    # uint16
        )

    def test_decimation_actually_shrinks_the_payload(self, solved):
        big = payload_bytes(encode_simulation(solved, max_transport_dim=256))
        small = payload_bytes(encode_simulation(solved, max_transport_dim=32))
        assert small < big / 4

    def test_extra_meta_is_merged(self, solved):
        payload = encode_simulation(solved, max_transport_dim=64,
                                    extra_meta={"scene_id": "test_scene"})
        assert payload["meta"]["scene_id"] == "test_scene"

    def test_encoding_an_empty_solve_fails_loudly(self):
        """
        A single-frame request asks only for the end state, so a solve that
        never gets there has genuinely nothing to encode. It must say so
        rather than emitting an empty animation.
        """
        empty = solve(
            synthetic_valley(40, 40), 30.0, duration_s=3600.0, n_frames=1,
            open_edges="auto", max_steps=0,
        )
        assert empty.depths == [] and empty.truncated
        with pytest.raises(ValueError, match="no frames"):
            encode_simulation(empty)
