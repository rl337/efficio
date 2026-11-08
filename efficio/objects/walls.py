"""Explicit material/process wall budgets, not structural certification.

Policies are supplied by projects. No universal thickness or material strength
is inferred. Measurements must state their scope and method separately.
"""

import math
from dataclasses import dataclass
from typing import Optional

from efficio.objects.fits import Process


@dataclass(frozen=True)
class WallPolicy:
    material: str
    process: Process
    environment: str
    minimum_mm: float
    basis: str
    required_features: tuple[str, ...]
    feature_limits: tuple[tuple[str, float], ...] = ()
    qualification: str = "provisional; physical validation required"

    def __post_init__(self) -> None:
        if not all(
            s.strip()
            for s in (self.material, self.environment, self.basis, self.qualification)
        ):
            raise ValueError(
                "wall policy needs material, environment, basis and qualification"
            )
        if not self.required_features or len(set(self.required_features)) != len(
            self.required_features
        ):
            raise ValueError("wall policy needs distinct required features")
        names = [n for n, _ in self.feature_limits]
        if len(set(names)) != len(names) or set(names) - set(self.required_features):
            raise ValueError("feature exceptions must name distinct required features")
        if not all(
            math.isfinite(v) and v > 0
            for v in (self.minimum_mm, *(v for _, v in self.feature_limits))
        ):
            raise ValueError("wall thresholds must be positive and finite")

    def violations(self, measurements: dict[str, float]) -> list[str]:
        errors = [
            "missing measurement: " + n
            for n in self.required_features
            if n not in measurements
        ]
        limits = dict(self.feature_limits)
        for name, value in measurements.items():
            minimum = limits.get(name, self.minimum_mm)
            if not math.isfinite(value) or value < minimum - 1e-9:
                errors.append(f"{name}: {value:g} mm below {minimum:g} mm policy")
        return errors

    def require(self, measurements: dict[str, float]) -> None:
        errors = self.violations(measurements)
        if errors:
            raise ValueError("; ".join(errors))


@dataclass(frozen=True)
class MaterialWallProfile:
    """Finished-wall policy plus independent tool-size assumptions.

    None means unqualified, not zero shrinkage or a guessed minimum. Allowance
    is TOTAL linear material removed along the dimension, not a per-face value.
    """

    name: str
    process: Process
    policy: Optional[WallPolicy] = None
    linear_shrinkage: Optional[float] = None
    machining_allowance_mm: float = 0.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("profile needs a name")
        if self.policy is not None and self.policy.process != self.process:
            raise ValueError("profile and wall policy processes differ")
        if self.linear_shrinkage is not None and not 0 <= self.linear_shrinkage < 1:
            raise ValueError("linear shrinkage must be in [0, 1)")
        if (
            not math.isfinite(self.machining_allowance_mm)
            or self.machining_allowance_mm < 0
        ):
            raise ValueError("machining allowance must be nonnegative and finite")

    def finished_policy(self) -> WallPolicy:
        if self.policy is None:
            raise ValueError(f"{self.name}: finished-wall profile is unqualified")
        return self.policy

    def tool_dimension(self, finished_mm: float) -> float:
        if not math.isfinite(finished_mm) or finished_mm <= 0:
            raise ValueError("finished dimension must be positive and finite")
        if self.linear_shrinkage is None:
            raise ValueError(f"{self.name}: shrinkage has not been measured")
        return (finished_mm + self.machining_allowance_mm) / (1 - self.linear_shrinkage)
