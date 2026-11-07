"""Pure sizing inputs; no seal qualification is implied."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GasketParameters:
    free_thickness: float
    outer_inset: float
    inner_inset: float
    spread_margin: float = 1.25
    minimum_width: float = 1.0
    round_to_width: bool = False

    def problems(self) -> list[str]:
        values = (
            self.free_thickness,
            self.outer_inset,
            self.inner_inset,
            self.spread_margin,
            self.minimum_width,
        )
        if not all(math.isfinite(v) for v in values):
            return ["gasket parameters must be finite"]
        if self.free_thickness <= 0 or min(self.outer_inset, self.inner_inset) < 0:
            return ["thickness must be positive and insets nonnegative"]
        if self.minimum_width <= 0:
            return ["minimum sealing width must be positive"]
        if self.spread_margin < 1:
            return ["spread margin must be at least one; it is not a safety factor"]
        return []
