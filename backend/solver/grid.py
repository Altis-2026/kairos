import heapq

import numpy as np

EDGES = {
    "north": (0, slice(None)),
    "south": (-1, slice(None)),
    "west": (slice(None), 0),
    "east": (slice(None), -1),
}

EDGE_NAMES = tuple(EDGES)


def validate_edges(open_edges) -> tuple:
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
    return tuple(dict.fromkeys(edges))


def lowest_edge(dem: np.ndarray) -> str:
    means = {name: float(np.mean(dem[sl])) for name, sl in EDGES.items()}
    return min(means, key=means.get)


def resolve_open_edges(dem: np.ndarray, open_edges) -> tuple:
    edges = validate_edges(open_edges)
    if edges == ("auto",):
        return (lowest_edge(dem),)
    return edges


def check_uniform_grid(dem: np.ndarray, dx: float) -> None:
    if dem.ndim != 2:
        raise ValueError(f"DEM must be 2-D (ny, nx); got shape {dem.shape}.")
    if min(dem.shape) < 3:
        raise ValueError(f"DEM must be at least 3x3 to have an interior; got {dem.shape}.")
    if not np.isfinite(dem).all():
        raise ValueError(
            "DEM contains NaN or infinite values. Fill nodata before solving, "
            "a single non-finite cell poisons the whole free-surface gradient."
        )
    if not np.isfinite(dx) or dx <= 0:
        raise ValueError(f"dx must be a positive, finite cell size in metres; got {dx}.")


def fill_pits(dem: np.ndarray) -> np.ndarray:
    filled = np.array(dem, dtype=np.float64, copy=True)
    ny, nx = filled.shape
    closed = np.zeros((ny, nx), dtype=bool)

    heap: list = []
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
            filled[rr, cc] = max(filled[rr, cc], z)
            heapq.heappush(heap, (filled[rr, cc], rr, cc))

    return filled
