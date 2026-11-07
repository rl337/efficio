"""Pure dimensions for integral hose terminals, all dimensions in mm."""

import math
from dataclasses import dataclass
from typing import Optional

from efficio.objects.connectors.sizes import HoseSize


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
    root_radius: float = 0.0
    root_length: float = 0.0

    def __post_init__(self) -> None:
        errors = self.problems()
        if errors:
            raise ValueError(errors[0])

    def problems(self) -> list[str]:
        values = [
            v
            for k, v in vars(self).items()
            if k not in {"barb_starts", "root_radius", "root_length"}
        ]
        if not all(math.isfinite(v) and v > 0 for v in values):
            return ["hose terminal dimensions must be finite and positive"]
        if not all(
            math.isfinite(v) and v >= 0 for v in (self.root_radius, self.root_length)
        ):
            return ["root dimensions must be finite and nonnegative"]
        if bool(self.root_radius) != bool(self.root_length):
            return ["root radius and length must be specified together"]
        if self.root_radius and (
            self.root_radius <= self.stem_radius or self.root_length > self.hose_start
        ):
            return ["root must broaden the stem and end before hose engagement"]
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

    @classmethod
    def from_size(
        cls,
        size: HoseSize,
        *,
        bore_radius: float,
        minimum_wall: float,
        hose_wall: Optional[float],
        length: float,
        barb_height: float,
        barb_length: float,
        barb_starts: tuple[float, ...],
        hose_start: float,
        clamp_length: float,
        clamp_clearance: float,
        root_extra_radius: float = 0.0,
        root_length: float = 0.0,
    ) -> "HoseBarbDimensions":
        """Resolve nominal ID separately from crest, OD and material wall budget."""
        if not math.isfinite(minimum_wall) or minimum_wall <= 0:
            raise ValueError("minimum wall must be positive and finite")
        known_wall = None if size.od_mm is None else (size.od_mm - size.id_mm) / 2
        if hose_wall is None:
            if known_wall is None:
                raise ValueError(
                    "nominal ID does not specify hose OD; provide hose wall"
                )
            hose_wall = known_wall
        elif known_wall is not None and abs(hose_wall - known_wall) > 1e-9:
            raise ValueError("hose wall conflicts with the selected product OD")
        stem = size.id_mm / 2
        if stem - bore_radius < minimum_wall - 1e-9:
            raise ValueError("selected hose ID cannot retain bore and minimum wall")
        return cls(
            bore_radius,
            stem,
            length,
            stem + barb_height,
            barb_length,
            barb_starts,
            size.id_mm,
            hose_wall,
            hose_start,
            clamp_length,
            clamp_clearance,
            stem + root_extra_radius if root_length else 0.0,
            root_length,
        )

    @property
    def finished_wall(self) -> float:
        return self.stem_radius - self.bore_radius

    @property
    def access_radius(self) -> float:
        return self.barb_radius + self.hose_wall + self.clamp_clearance
