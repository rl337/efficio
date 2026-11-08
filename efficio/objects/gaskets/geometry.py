"""Pure sizing inputs; no seal qualification is implied."""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class GasketParameters:
    free_thickness: float = 2.0
    outer_inset: Optional[float] = None
    inner_inset: Optional[float] = None
    spread_margin: float = 1.25
    minimum_width: float = 1.0
    round_to_width: bool = False
    # Keyword-only preserves the existing positional argument order.
    inset: float = field(default=0.4, kw_only=True)

    @property
    def resolved_outer_inset(self) -> float:
        return self.inset if self.outer_inset is None else self.outer_inset

    @property
    def resolved_inner_inset(self) -> float:
        return self.inset if self.inner_inset is None else self.inner_inset

    def problems(self) -> list[str]:
        values = (
            self.free_thickness,
            self.inset,
            self.resolved_outer_inset,
            self.resolved_inner_inset,
            self.spread_margin,
            self.minimum_width,
        )
        if not all(math.isfinite(v) for v in values):
            return ["gasket parameters must be finite"]
        if (
            self.free_thickness <= 0
            or min(self.inset, self.resolved_outer_inset, self.resolved_inner_inset) < 0
        ):
            return ["thickness must be positive and insets nonnegative"]
        if self.minimum_width <= 0:
            return ["minimum sealing width must be positive"]
        if self.spread_margin < 1:
            return ["spread margin must be at least one; it is not a safety factor"]
        return []
