"""
Volume bookkeeping for the hydraulic solver.

The solver's central claim is that it is mass-conservative by construction:
water leaving one cell across a face is exactly the water entering its
neighbour. That claim is only worth anything if it is *measured*, so every
solve carries a ledger and reports its own closure error alongside the
result — the same discipline the SAR analyses follow when they report
threshold spread instead of a single confident number.

The identity that must hold at every step, exactly:

    stored = initial + injected + rained - discharged - infiltrated

`mass_error` is the residual of that identity, normalised by the largest
volume the domain has held. Anything above ~1e-9 means a bug, not a
tolerance: the scheme has no diffusion term that could legitimately lose
water.
"""

from dataclasses import dataclass, field


@dataclass
class VolumeLedger:
    """Cumulative water volumes in m³ for one solve."""

    initial: float = 0.0
    injected: float = 0.0      # inflow hydrograph
    rained: float = 0.0        # rainfall source term
    discharged: float = 0.0    # through open boundaries
    infiltrated: float = 0.0   # infiltration / loss sink
    stored: float = 0.0        # current volume on the grid

    # Largest volume the domain has held; the normaliser for mass_error.
    peak: float = field(default=0.0)

    def observe(self, stored: float) -> None:
        """Record the current stored volume."""
        self.stored = stored
        self.peak = max(self.peak, stored)

    @property
    def expected(self) -> float:
        """Stored volume implied by the source/sink accounting."""
        return (
            self.initial
            + self.injected
            + self.rained
            - self.discharged
            - self.infiltrated
        )

    @property
    def residual(self) -> float:
        """Absolute closure error in m³ (signed: positive means water created)."""
        return self.stored - self.expected

    @property
    def mass_error(self) -> float:
        """
        Closure error relative to the largest volume the domain has held.

        Normalising by `peak` rather than by `stored` keeps the number
        meaningful during recession, when `stored` tends toward zero and a
        relative error against it would blow up for no physical reason.
        """
        scale = max(self.peak, self.initial + self.injected + self.rained)
        if scale <= 0.0:
            return 0.0
        return self.residual / scale

    def as_dict(self) -> dict:
        """Serializable summary — surfaced in the API payload and the UI."""
        return {
            "initial_m3": self.initial,
            "injected_m3": self.injected,
            "rained_m3": self.rained,
            "discharged_m3": self.discharged,
            "infiltrated_m3": self.infiltrated,
            "stored_m3": self.stored,
            "peak_stored_m3": self.peak,
            "residual_m3": self.residual,
            "mass_error": self.mass_error,
        }
