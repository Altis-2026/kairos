"""
Kairos forward-model solvers.

Everything in this package is pure NumPy: no Earth Engine, no network, no
PyTorch. That is deliberate — the numerics are unit-testable offline, in the
same "pure function" spirit as the analysis pipeline in `gee/`.

Outputs from this package are **simulated**, never observed. Anything that
surfaces them to a user or to the AI layer must label them as model output and
keep them visually and semantically distinct from the SAR detections.
"""

from solver.diagnostics import VolumeLedger
from solver.hydraulic_route import SolveResult, run_event, solve

__all__ = ["SolveResult", "VolumeLedger", "run_event", "solve"]
