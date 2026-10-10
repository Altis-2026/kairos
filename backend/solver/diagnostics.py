from dataclasses import dataclass, field


@dataclass
class VolumeLedger:
    initial: float = 0.0
    injected: float = 0.0
    rained: float = 0.0
    discharged: float = 0.0
    infiltrated: float = 0.0
    stored: float = 0.0

    peak: float = field(default=0.0)

    def observe(self, stored: float) -> None:
        self.stored = stored
        self.peak = max(self.peak, stored)

    @property
    def expected(self) -> float:
        return self.initial + self.injected + self.rained - self.discharged - self.infiltrated

    @property
    def residual(self) -> float:
        return self.stored - self.expected

    @property
    def mass_error(self) -> float:
        scale = max(self.peak, self.initial + self.injected + self.rained)
        if scale <= 0.0:
            return 0.0
        return self.residual / scale

    def as_dict(self) -> dict:
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
