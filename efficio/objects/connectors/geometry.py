"""Pure dimensions for integral hose terminals, all dimensions in mm."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class HoseBarbDimensions:
    bore_radius: float
    stem_radius: float
    length: float
    barb_radius: float
    barb_length: float
    barb_starts: tuple[float, ...]
    hose_id: float
    hose_wall: float
    hose_start: float
    clamp_length: float
    clamp_clearance: float

    def __post_init__(self) -> None:
        errors = self.problems()
        if errors:
            raise ValueError(errors[0])

    def problems(self) -> list[str]:
        values = [v for k, v in vars(self).items() if k != "barb_starts"]
        if not all(math.isfinite(v) and v > 0 for v in values):
            return ["hose terminal dimensions must be finite and positive"]
        if not self.bore_radius < self.stem_radius < self.barb_radius:
            return ["bore, stem and barb radii must be ordered"]
        if not self.barb_starts or not all(math.isfinite(v) for v in self.barb_starts):
            return ["terminal requires finite barb locations"]
        if self.hose_id > 2 * self.stem_radius:
            return ["hose ID exceeds sealing land diameter"]
        if self.hose_start + self.clamp_length > min(self.barb_starts):
            return ["clamp land overlaps barb shoulders"]
        for i, start in enumerate(self.barb_starts):
            if start < self.hose_start or start + self.barb_length > self.length:
                return ["barbs must lie inside hose engagement"]
            if i and start < self.barb_starts[i - 1] + self.barb_length:
                return ["barbs overlap or are out of order"]
        return []

    @property
    def finished_wall(self) -> float:
        return self.stem_radius - self.bore_radius

    @property
    def access_radius(self) -> float:
        return self.barb_radius + self.hose_wall + self.clamp_clearance
