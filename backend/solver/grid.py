"""
Grid conventions and DEM conditioning for the hydraulic solver.

Array orientation
-----------------
A DEM is a 2-D array indexed ``dem[row, col]`` with shape ``(ny, nx)``.
Row 0 is the NORTH edge and row ``ny-1`` is the SOUTH edge, matching how a
north-up raster is stored on disk; column 0 is WEST and column ``nx-1`` is
EAST. Every edge name in this package resolves through `EDGES` below, so the
convention is stated in exactly one place.

The solver assumes a single uniform cell size `dx` in **metres in both
directions**. That is a real constraint, not a convenience: a DEM sampled on
a lat/lon grid has x-spacing shrinking as cos(latitude) while y-spacing stays
fixed, so at 45° north a "square" cell is 30 m tall and 21 m wide. Feeding
such a grid to this solver routes water at a systematically wrong angle,
everywhere, silently. Rasters must therefore be resampled into a metric
projection (UTM or equivalent) before they reach `run_event`. The fetch layer
owns that reprojection; `check_uniform_grid` here is the assertion that it
happened.
"""

import heapq

import numpy as np

# Edge name -> the slice selecting that border row/column of a (ny, nx) array.
EDGES = {
    "north": (0, slice(None)),
    "south": (-1, slice(None)),
    "west": (slice(None), 0),
    "east": (slice(None), -1),
}

EDGE_NAMES = tuple(EDGES)


def validate_edges(open_edges) -> tuple:
    """
    Normalise the `open_edges` argument to a tuple of valid edge names.

    Accepts an iterable of names, the string ``"auto"``, or None/empty for a
    fully closed (reflective) domain.
    """
    if open_edges is None:
        return ()
    if isinstance(open_edges, str):
        open_edges = (open_edges,)
    edges = tuple(open_edges)
    if edges == ("auto",):
        return edges
    unknown = [e for e in edges if e not in EDGES]
    if unknown:
        raise ValueError(
            f"Unknown open edge(s) {unknown}. Valid edges: {list(EDGE_NAMES)} "
            f"(or 'auto' to pick the lowest-lying edge)."
        )
    return tuple(dict.fromkeys(edges))  # de-duplicate, preserve order


def lowest_edge(dem: np.ndarray) -> str:
    """
    The edge with the lowest mean elevation — the domain's natural outlet.

    Used to resolve ``open_edges='auto'``. Mean rather than minimum, so one
    anomalous low pixel on an otherwise high wall cannot claim the outlet.
    """
    means = {name: float(np.mean(dem[sl])) for name, sl in EDGES.items()}
    return min(means, key=means.get)


def resolve_open_edges(dem: np.ndarray, open_edges) -> tuple:
    """Turn the user-facing `open_edges` argument into concrete edge names."""
    edges = validate_edges(open_edges)
    if edges == ("auto",):
        return (lowest_edge(dem),)
    return edges


def check_uniform_grid(dem: np.ndarray, dx: float) -> None:
    """
    Validate the terrain array and cell size the solver was handed.

    Raises ValueError rather than warning: every one of these conditions
    produces a plausible-looking animation from wrong physics.
    """
    if dem.ndim != 2:
        raise ValueError(f"DEM must be 2-D (ny, nx); got shape {dem.shape}.")
    if min(dem.shape) < 3:
        raise ValueError(
            f"DEM must be at least 3x3 to have an interior; got {dem.shape}."
        )
    if not np.isfinite(dem).all():
        raise ValueError(
            "DEM contains NaN or infinite values. Fill nodata before solving — "
            "a single non-finite cell poisons the whole free-surface gradient."
        )
    if not np.isfinite(dx) or dx <= 0:
        raise ValueError(f"dx must be a positive, finite cell size in metres; got {dx}.")


def fill_pits(dem: np.ndarray) -> np.ndarray:
    """
    Priority-flood depression filling (Barnes et al. 2014).

    Raw DEMs contain sinks — some real, many artefacts of the sensor or the
    void-filling that produced them. Water routed into an artefact sink stays
    there forever, so a simulation over an unconditioned DEM can show a flood
    that never recedes for reasons that have nothing to do with hydraulics.

    This is deliberately NOT applied automatically. Filling pits changes the
    terrain, and a terrain change that the user did not ask for and cannot see
    is exactly the kind of silent fabrication this package is trying to avoid.
    Callers opt in and the result is labelled.

    Returns a new array; the input is untouched.
    """
    filled = np.array(dem, dtype=np.float64, copy=True)
    ny, nx = filled.shape
    closed = np.zeros((ny, nx), dtype=bool)

    heap: list = []
    # Seed with the domain border: water can always escape from there.
    for r in range(ny):
        for c in (0, nx - 1):
            heapq.heappush(heap, (filled[r, c], r, c))
            closed[r, c] = True
    for c in range(1, nx - 1):
        for r in (0, ny - 1):
            heapq.heappush(heap, (filled[r, c], r, c))
            closed[r, c] = True

    while heap:
        z, r, c = heapq.heappop(heap)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = r + dr, c + dc
            if rr < 0 or rr >= ny or cc < 0 or cc >= nx or closed[rr, cc]:
                continue
            closed[rr, cc] = True
            # Raise the neighbour to at least the level of the cell it drains
            # through: that is what makes the pit disappear.
            filled[rr, cc] = max(filled[rr, cc], z)
            heapq.heappush(heap, (filled[rr, cc], rr, cc))

    return filled
